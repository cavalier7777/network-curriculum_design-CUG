from typing import Dict, List, Optional
import time
import json
import asyncio

class NetworkManager:
    """
    Manages the global state of the network for visualization.
    Receives reports from nodes and aggregates them.
    """
    def __init__(self):
        # Nodes state: { node_id: { last_seen, routing_table, neighbors, logs } }
        self.nodes: Dict[str, dict] = {}
        self.lock = asyncio.Lock()
        
        # Command Queue: { node_id: [cmd1, cmd2] }
        self.pending_commands: Dict[str, List[str]] = {}

    async def update_node(self, node_id: str, data: dict):
        async with self.lock:
            self.nodes[node_id] = {
                "last_seen": time.time(),
                "routing_table": data.get("routing_table", {}),
                "neighbors": data.get("neighbors", []),
                "ip": data.get("ip", ""), # Virtual IP/ID
                "details": data
            }
            # Initialize command queue if needed
            if node_id not in self.pending_commands:
                self.pending_commands[node_id] = []

    async def get_commands(self, node_id: str) -> List[str]:
        async with self.lock:
            cmds = self.pending_commands.get(node_id, [])
            self.pending_commands[node_id] = []
            return cmds

    async def queue_command(self, node_id: str, command: str):
        async with self.lock:
            if node_id == "BROADCAST":
                for nid in self.nodes:
                    self.pending_commands.setdefault(nid, []).append(command)
            else:
                self.pending_commands.setdefault(node_id, []).append(command)

    async def get_topology(self):
        """
        Constructs a graph format suitable for frontend (e.g., react-force-graph).
        nodes: [{id, idx, val, ...}]
        links: [{source, target, label...}]
        """
        async with self.lock:
            graph_nodes = []
            graph_links = []
            
            # Filter out stale nodes (e.g., > 10 seconds silent) ? 
            # For now, keep them but mark inactive?
            current_time = time.time()
            
            for nid, info in self.nodes.items():
                is_active = (current_time - info["last_seen"]) < 5.0
                graph_nodes.append({
                    "id": nid,
                    "name": nid,
                    "val": 10 if is_active else 5,
                    "color": "#4CAF50" if is_active else "#9E9E9E",
                    # "table": info["routing_table"] # Too large, maybe send on demand
                })
                
                # Links based on routing table or direct neighbors?
                # Neighbors is better for physical links.
                # Routing table next_hops implies logical paths.
                # Let's use neighbors for 'physical' topology.
                neighbors = info.get("neighbors", [])
                # neighbors structure from report: {port: {id: ..., cost: ...}} or list
                # We'll assume the report sends a simplified list of neighbor IDs.
                
                # Deduplicate links? (A->B and B->A is one link)
                # Frontend is usually fine with A->B.
                for neighbor_id in neighbors:
                    # Only add if neighbor is known or we want to show partials
                    graph_links.append({
                        "source": nid,
                        "target": neighbor_id,
                        "color": "#FFF"
                    })

            return {
                "nodes": graph_nodes,
                "links": graph_links
            }

    async def get_node_details(self, node_id: str):
        async with self.lock:
            return self.nodes.get(node_id, {})

# Global instance
manager = NetworkManager()
