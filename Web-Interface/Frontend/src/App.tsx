
import React, { useEffect, useState, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

// Simple interface for graph data
interface GraphData {
  nodes: { id: string, name: string, val: number }[];
  links: { source: string, target: string }[];
}

function App() {
  const [logs, setLogs] = useState<string[]>([]);
  const [cmd, setCmd] = useState("");
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const ws = useRef<WebSocket | null>(null);
  const logEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Connect to Backend
    ws.current = new WebSocket("ws://localhost:8000/ws");
    
    ws.current.onopen = () => {
      addLog("System: Connected to Network Node Backend.");
    };

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'log') {
        addLog(msg.data);
      } else if (msg.type === 'topo') {
        updateGraph(msg.data);
      }
    };

    return () => {
      ws.current?.close();
    };
  }, []);

  // Auto-scroll to bottom of logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const addLog = (text: string) => {
    setLogs(prev => [...prev.slice(-100), text]); // Keep last 100 lines
  };

  const updateGraph = (topo: any) => {
    // Transform backend topology data to graph format
    // topo.table = { "B": {cost:1, ...}, ... }
    const nodes = [{ id: topo.id, name: topo.id + " (Me)", val: 10 }];
    const links: any[] = [];
    
    // Add neighbors from routing table as nodes and links
    Object.keys(topo.table).forEach(dest => {
       if (dest !== topo.id) {
           nodes.push({ id: dest, name: dest, val: 5 });
           // If direct neighbor (cost 1 or defined in neighbors), add link
           // Simplified visualization
           links.push({ source: topo.id, target: dest });
       }
    });

    setGraphData({ nodes, links });
  };

  const sendCommand = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ws.current || !cmd) return;
    
    ws.current.send(JSON.stringify({ type: 'command', data: cmd }));
    setCmd("");
  };

  return (
    <div style={styles.container}>
      <style>{`
        /* Custom Scrollbar for Terminal */
        .terminal-scroll::-webkit-scrollbar {
          width: 8px;
        }
        .terminal-scroll::-webkit-scrollbar-track {
          background: #1a1a1a; 
        }
        .terminal-scroll::-webkit-scrollbar-thumb {
          background: #444; 
          border-radius: 4px;
        }
        .terminal-scroll::-webkit-scrollbar-thumb:hover {
          background: #666; 
        }
        body { margin: 0; padding: 0; background: #0d1117; }
        
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.4); }
          70% { box-shadow: 0 0 0 10px rgba(74, 222, 128, 0); }
          100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }
        }
      `}</style>

      {/* Header */}
      <header style={styles.header}>
        <div style={styles.brand}>
          <div style={styles.logoIcon}>📡</div>
          <div>
            <h1 style={styles.title}>Network Admin Console</h1>
            <span style={styles.subtitle}>Experiment 6 • Distributed Routing Control</span>
          </div>
        </div>
        <div style={styles.statusBadge}>
          <span style={styles.statusDot}></span>
          <span>Online</span>
        </div>
      </header>
      
      {/* Main Content */}
      <main style={styles.main}>
        {/* Graph Area */}
        <section style={styles.graphSection}>
          <div style={styles.panelHeader}>
            <span style={styles.panelTitle}>Network Topology</span>
            <div style={styles.panelControls}>
              <span style={{...styles.controlDot, background:'#ff5f56'}}></span>
              <span style={{...styles.controlDot, background:'#ffbd2e'}}></span>
              <span style={{...styles.controlDot, background:'#27c93f'}}></span>
            </div>
          </div>
          <div style={styles.graphContainer}>
            <ForceGraph2D
                graphData={graphData}
                nodeLabel="name"
                nodeAutoColorBy="id"
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                backgroundColor="#0d1117"
                linkColor={() => '#30363d'}
                nodeRelSize={6}
            />
            <div style={styles.overlayInfo}>
              Nodes: {graphData.nodes.length} | Links: {graphData.links.length}
            </div>
          </div>
        </section>

        {/* Console Area */}
        <section style={styles.consoleSection}>
          <div style={styles.panelHeader}>
            <span style={styles.panelTitle}>Terminal Output</span>
            <span style={styles.sshBadge}>SSH: Localhost:8000</span>
          </div>
          
          <div className="terminal-scroll" style={styles.terminalBody}>
              {logs.length === 0 && (
                <div style={styles.emptyState}>
                  Waiting for connection... <br/>
                  Enter <code>help</code> for commands.
                </div>
              )}
              {logs.map((L, i) => (
                  <div key={i} style={styles.logLine}>
                    <span style={styles.promptChar}>➜</span> {L}
                  </div>
              ))}
              <div ref={logEndRef} />
          </div>

          <form onSubmit={sendCommand} style={styles.commandBar}>
              <span style={styles.commandPrompt}>admin@node:~$</span>
              <input 
                  value={cmd}
                  onChange={e => setCmd(e.target.value)}
                  style={styles.input}
                  placeholder="Enter command (e.g., ping B, tracert C)..."
                  autoFocus
              />
              <button type="submit" style={styles.sendBtn}>SEND</button>
          </form>
        </section>
      </main>
    </div>
  )
}

// CSS-in-JS Styles
const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex', 
    flexDirection: 'column', 
    height: '100vh', 
    fontFamily: '"Segoe UI", "Roboto", sans-serif',
    background: '#010409',
    color: '#c9d1d9',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '15px 25px',
    background: '#161b22',
    borderBottom: '1px solid #30363d',
    boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
    zIndex: 10,
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logoIcon: {
    fontSize: '24px',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
    color: '#f0f6fc',
  },
  subtitle: {
    display: 'block',
    fontSize: '12px',
    color: '#8b949e',
    marginTop: '2px',
  },
  statusBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 12px',
    background: 'rgba(56, 139, 253, 0.1)',
    border: '1px solid rgba(56, 139, 253, 0.4)',
    borderRadius: '20px',
    fontSize: '12px',
    color: '#58a6ff',
    fontWeight: 500,
  },
  statusDot: {
    width: '8px',
    height: '8px',
    background: '#3fb950',
    borderRadius: '50%',
    boxShadow: '0 0 8px #3fb950',
    animation: 'pulse 2s infinite',
  },
  main: {
    flex: 1,
    display: 'flex',
    overflow: 'hidden',
    padding: '15px',
    gap: '15px',
  },
  graphSection: {
    flex: 3,
    display: 'flex',
    flexDirection: 'column',
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '8px',
    overflow: 'hidden',
    boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
  },
  panelHeader: {
    padding: '10px 15px',
    background: '#161b22',
    borderBottom: '1px solid #30363d',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '13px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: '#8b949e',
  },
  panelControls: {
    display: 'flex',
    gap: '6px',
  },
  controlDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
  },
  graphContainer: {
    flex: 1,
    position: 'relative',
  },
  overlayInfo: {
    position: 'absolute',
    bottom: '15px',
    left: '15px',
    padding: '5px 10px',
    background: 'rgba(22, 27, 34, 0.8)',
    borderRadius: '4px',
    fontSize: '12px',
    color: '#8b949e',
    border: '1px solid #30363d',
    pointerEvents: 'none',
  },
  consoleSection: {
    flex: 2,
    display: 'flex',
    flexDirection: 'column',
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '8px',
    overflow: 'hidden',
    maxWidth: '500px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
  },
  sshBadge: {
    fontSize: '10px',
    background: '#238636',
    color: 'white',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  terminalBody: {
    flex: 1,
    overflowY: 'auto',
    padding: '15px',
    fontFamily: '"JetBrains Mono", "Fira Code", Consolas, monospace',
    fontSize: '13px',
    lineHeight: '1.6',
    background: 'rgba(0,0,0,0.2)',
  },
  emptyState: {
    color: '#484f58',
    textAlign: 'center',
    marginTop: '50px',
    fontStyle: 'italic',
  },
  logLine: {
    wordBreak: 'break-all',
    marginBottom: '4px',
    color: '#c9d1d9',
  },
  promptChar: {
    color: '#2f81f7',
    marginRight: '8px',
    fontWeight: 'bold',
  },
  commandBar: {
    display: 'flex',
    alignItems: 'center',
    background: '#161b22',
    borderTop: '1px solid #30363d',
    padding: '10px',
  },
  commandPrompt: {
    color: '#3fb950',
    fontFamily: 'Consolas, monospace',
    fontSize: '13px',
    marginRight: '10px',
    fontWeight: 'bold',
  },
  input: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    color: '#fff',
    outline: 'none',
    fontFamily: 'Consolas, monospace',
    fontSize: '13px',
  },
  sendBtn: {
    background: '#238636',
    border: 'none',
    color: '#fff',
    padding: '6px 12px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.2s',
  }
};

export default App
