
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
import asyncio
import json
import threading
import os
from contextlib import asynccontextmanager
from terminal_session import TerminalSession
from network_manager import manager  # Import the manager
from pydantic import BaseModel
from typing import Dict, List, Any

# Set paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, '../Frontend/dist')

# Global Node Instance
terminal_instance = None
active_websockets = []
loop = None

class NodeReport(BaseModel):
    node_id: str
    routing_table: Dict[str, Any]
    neighbors: List[str]
    logs: List[str] = []

def broadcast_log(msg: str):
    # print(f"[TERM] {msg}") # Optional server-side logging
    for websocket in active_websockets:
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({"type": "log", "data": msg}), 
                loop
            )

def broadcast_topo(data: dict):
    for websocket in active_websockets:
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({"type": "topo", "data": data}), 
                loop
            )

async def periodic_topo_broadcast():
    while True:
        try:
            topo = await manager.get_topology()
            broadcast_topo(topo)
        except Exception as e:
            print(f"Bcast Error: {e}")
        await asyncio.sleep(1.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global terminal_instance, loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
        
    print(f"Initializing TerminalSession...")
    # Initialize Terminal Session (Legacy support)
    terminal_instance = TerminalSession(
        log_callback=broadcast_log,
        topo_callback=broadcast_topo
    )
    print(f"TerminalSession Ready.")

    # Start Manager Broadcast Task
    asyncio.create_task(periodic_topo_broadcast())
    
    yield
    
    print("Shutting down...")
    # Cleanup logic if needed

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === API FOR NODES ===

@app.post("/api/report")
async def report_node_state(report: NodeReport):
    """Nodes POST here to update their state"""
    # 1. Update Manager
    await manager.update_node(report.node_id, report.model_dump())
    
    # 2. Forward live logs to frontend immediately
    if report.logs:
        for log in report.logs:
            broadcast_log(f"[{report.node_id}] {log}")
            
    # 3. Return pending commands
    cmds = await manager.get_commands(report.node_id)
    return {"commands": cmds}

@app.post("/api/command")
async def send_command(data: dict):
    """Frontend POSTs here to send command to a node"""
    node_id = data.get("node_id")
    cmd = data.get("command")
    if node_id and cmd:
        await manager.queue_command(node_id, cmd)
        return {"status": "queued"}
    return {"status": "error"}

@app.get("/api/nodes/{node_id}")
async def get_node_detail(node_id: str):
    return await manager.get_node_details(node_id)

# === END API ===

@app.get("/api/health")
async def health_check():
    return JSONResponse({"status": "ok", "mode": "static_serving" if os.path.exists(DIST_DIR) else "backend_only"})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message['type'] == 'command':
                cmd = message['data']
                if terminal_instance:
                    terminal_instance.write(cmd)
                    
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        if websocket in active_websockets:
            active_websockets.remove(websocket)

# Serve React App
# Verify dist directory exists to avoid errors if not built
if os.path.exists(DIST_DIR):
    print(f"Found React build at: {DIST_DIR}")
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="static")
else:
    print(f"Warning: React Build directory not found at {DIST_DIR}")
    print("Please run 'npm run build' in ../Frontend/")
    
    @app.get("/")
    async def root_warning():
        return JSONResponse({
            "error": "Frontend not built",
            "message": "Please run 'npm run build' in Web-Interface/Frontend directory.",
            "path_checked": DIST_DIR
        }, status_code=404)

if __name__ == "__main__":
    import sys
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}, using default 8000")
            
    print(f"Starting Backend on 0.0.0.0:{port}")
    print("Note: If accessing from another machine, ensure Windows Firewall allows python.exe")
    uvicorn.run(app, host="0.0.0.0", port=port)
