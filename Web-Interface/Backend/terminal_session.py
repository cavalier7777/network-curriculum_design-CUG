import sys
import os
import asyncio
from network_manager import manager

class TerminalSession:
    """
    Acts as a Global Command Console for the Network.
    Parses commands like: 'A ping B' and routes them to Node A.
    """
    def __init__(self, log_callback, topo_callback):
        self.log_callback = log_callback
        self.topo_callback = topo_callback
        self.line_buffer = ""
        
        # Initial greeting
        self.show_welcome()
    
    def show_welcome(self):
        msg = [
            "\r\n\x1b[1;36m=== Global Network Controller ===\x1b[0m",
            "Command Syntax: <NodeID> <Command>",
            "Example: 'A ping B'",
            "         'A tracert C'",
            "         'A table'",
            "-----------------------------------"
        ]
        self.log_callback("\r\n".join(msg) + "\r\n> ")

    def write(self, data):
        """Handle input from WebSocket (char by char usually)"""
        # Echo back
        self.log_callback(data)
        
        if data == '\r': # Enter key
            self.log_callback('\n')
            self.process_line(self.line_buffer.strip())
            self.line_buffer = ""
            self.log_callback("> ")
        elif data == '\x7f': # Backspace
            if len(self.line_buffer) > 0:
                self.line_buffer = self.line_buffer[:-1]
                # Send backspace sequence to terminal
                self.log_callback("\b \b")
        else:
            self.line_buffer += data

    def process_line(self, line):
        if not line: return
        
        parts = line.split(maxsplit=1)
        node_id = parts[0]
        
        # Check if node exists (async call wrap)
        # We can't await here directly as this is called from sync context usually, 
        # but main.py calls this.
        # However, main.py calls it from async websocket loop?
        # main.py does: terminal_instance.write(cmd) inside async def.
        # But write is sync.
        
        # We need to fire and forget or use asyncio.create_task
        loop = asyncio.get_event_loop()
        loop.create_task(self._dispatch_command(node_id, line))

    async def _dispatch_command(self, node_id, full_line):
        # Check if it's a broadcast or system command
        if node_id.lower() == 'help':
            self.show_welcome()
            return
            
        # Try to queue logic
        # Command syntax: <NodeID> <Rest>
        # User types: "A ping B"
        # NodeID=A, Rest="ping B"
        
        try:
            parts = full_line.split(maxsplit=1)
            if len(parts) < 2:
                self.log_callback(f"\r\n[System] Incomplete command. Usage: {node_id} <cmd>\r\n")
                return

            cmd_payload = parts[1]
            await manager.queue_command(node_id, cmd_payload)
            self.log_callback(f"\r\n[System] Queued command for {node_id}: {cmd_payload}\r\n")
            
        except Exception as e:
            self.log_callback(f"\r\n[System] Error: {e}\r\n")
            if data == '\r':
                cmd = self.current_buffer.strip()
                self.current_buffer = "" # Reset
                
                if cmd in MENU_OPTIONS:
                    self.launch(MENU_OPTIONS[cmd])
                else:
                    if cmd:
                        self.log_callback(f"Unknown option: {cmd}\r\n> ")
                    else:
                        self.log_callback("> ")
            elif data == '\x7f': # Backspace
                if len(self.current_buffer) > 0:
                    self.current_buffer = self.current_buffer[:-1]
                    # Visual backspace: Move back, Space, Move back
                    self.log_callback("\b \b") 
            else:
                self.current_buffer += data
                
            return

        # If process is running, write to stdin
        if self.process:
            try:
                # Add newline because most inputs expect it
                # But typical xterm sends \r, need to ensure python gets \n
                input_data = data
                if input_data == '\r': 
                    input_data = '\n'
                
                self.process.stdin.write(input_data.encode('utf-8'))
                self.process.stdin.flush()
            except IOError:
                pass

    def launch(self, option):
        script_path = option['script']
        cwd = option['cwd']
        name = option['name']

        self.log_callback(f"\r\n\x1b[1;32mStarting {name}...\x1b[0m\r\n")
        
        # Use python -u for unbuffered output
        cmd = [sys.executable, '-u', script_path]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Merge stderr to stdout
                cwd=cwd,
                bufsize=0 # Unbuffered
            )
            
            self.running = True
            self.thread = threading.Thread(target=self._monitor_output, daemon=True)
            self.thread.start()
            
        except Exception as e:
            self.log_callback(f"\r\nFailed to start process: {str(e)}\r\n> ")
            self.show_menu()

    def _monitor_output(self):
        """Read output from process"""
        while self.process and self.process.poll() is None:
            try:
                # Read char by char or line by line?
                # Line by line is safer for parsing, but char by char is better for interactive feel.
                # Since we used unbuffered, we can try to read small chunks.
                chunk = self.process.stdout.read(1)
                if not chunk:
                    break
                
                text = chunk.decode('utf-8', errors='ignore')
                
                # Send to terminal
                self.log_callback(text)
                
                # Buffer for logical parsing (Looking for Tables)
                self.current_buffer += text
                if '\n' in self.current_buffer:
                    lines = self.current_buffer.split('\n')
                    # Process complete lines
                    for line in lines[:-1]:
                        self._analyze_line(line)
                    # Keep incomplete line
                    self.current_buffer = lines[-1]
                    
                    # Also analyze accumulated buffer for multi-line tables if needed
                    # But _analyze_line can trigger a multi-line parser state machine
                    
            except Exception as e:
                break
        
        self.log_callback("\r\n\x1b[1;31mProcess exited.\x1b[0m\r\n")
        self.process = None
        self.show_menu()

    # --- Topology Parser State Machine ---
    _table_buffer = []
    _in_table = False

    def _analyze_line(self, line):
        # We are looking for something like:
        # ------- 当前路由表 (Distance Vector) -------
        # Destination     Cost       Next Hop        Interface
        # ...
        
        clean_line = line.strip()
        
        # Detect Start
        if "路由表" in clean_line or "Routing Table" in clean_line:
            self._in_table = True
            self._table_buffer = []
            return

        # Detect End (Empty line or separator line after content if we want strictness, 
        # but usually the next prompt or ----------- marks end)
        # For simplicity, if we are in table, we collect until we see a separator line at the end, 
        # OR we just parse on every line addition if we match the format.
        
        if self._in_table:
            self._table_buffer.append(clean_line)
            # If we see a separator line that might be the footer?
            # Or if it's the header separator.
            
            # Let's try to parse the buffer if it looks substantial
            if len(self._table_buffer) > 2:
                self._parse_table_buffer(self._table_buffer)
            
            # Reset if we hit an empty line or end separator
            if clean_line.startswith('---') and len(self._table_buffer) > 1:
                # Could be footer
                pass

    def _parse_table_buffer(self, lines):
        # Experiment 4 Format:
        # Destination     Cost       Next Hop        Interface
        # A               0          A               LOCAL
        
        # We need to find the data rows.
        # Ignore headers and separators.
        
        parsed_entries = {}
        my_id = "?"
        
        for l in lines:
            parts = l.split()
            if len(parts) >= 4:
                # Check if it looks like a data row: Dest(Str) Cost(Int) NextHop(Str) Interface(Str)
                dest, cost_str, next_hop, interface = parts[0], parts[1], parts[2], parts[3]
                
                if next_hop.upper() == "NEXT": continue # Header row
                
                try:
                    cost = int(cost_str)
                    parsed_entries[dest] = {
                        'cost': cost,
                        'next_hop': next_hop,
                        'interface': interface
                    }
                    if cost == 0:
                        my_id = dest
                except ValueError:
                    continue

        if parsed_entries and my_id != "?":
            # Send topology update
            topo_data = {
                'id': my_id,
                'table': parsed_entries
            }
            self.topo_callback(topo_data)
