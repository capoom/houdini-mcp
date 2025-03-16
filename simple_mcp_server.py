import json
import socket
import sys
import threading
import time

# Create a socket server for Houdini communication
class HoudiniSocketServer:
    def __init__(self, host='localhost', port=9877):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        
    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print(f"Connected to Houdini at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to Houdini: {str(e)}", file=sys.stderr)
            return False
            
    def send_command(self, cmd_type, params=None):
        if not self.sock:
            if not self.connect():
                return {"error": "Not connected to Houdini"}
        
        cmd = {"type": cmd_type, "params": params or {}}
        try:
            self.sock.sendall(json.dumps(cmd).encode('utf-8'))
            response = self.sock.recv(8192).decode('utf-8')
            return json.loads(response)
        except Exception as e:
            print(f"Error communicating with Houdini: {str(e)}", file=sys.stderr)
            return {"error": str(e)}

# Simple MCP server
def main():
    print("Starting simplified MCP server...", file=sys.stderr)
    
    # MCP Protocol specific constants
    PROTOCOL_VERSION = "2024-11-05"
    
    # Socket for the JSON-RPC server
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_sock.bind(('localhost', 8080))
        server_sock.listen(1)
        print("MCP Server listening on localhost:8080", file=sys.stderr)
        
        # Create Houdini connection
        houdini = HoudiniSocketServer()
        
        while True:
            client_sock, address = server_sock.accept()
            print(f"Client connected from {address}", file=sys.stderr)
            
            try:
                # Handle one request at a time
                data = client_sock.recv(4096).decode('utf-8')
                if not data:
                    continue
                
                print(f"Received: {data}", file=sys.stderr)
                
                request = json.loads(data)
                
                # Handle initialize request
                if request.get("method") == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "protocolVersion": PROTOCOL_VERSION,
                            "serverInfo": {
                                "name": "simple-houdini-mcp",
                                "version": "0.1.0"
                            },
                            "capabilities": {
                                "tools": {
                                    "get_scene_info": {
                                        "description": "Get information about the current Houdini scene"
                                    },
                                    "create_geometry": {
                                        "description": "Create a primitive geometry object",
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "geo_type": {
                                                    "type": "string",
                                                    "description": "Type of geometry to create",
                                                    "default": "box"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    client_sock.sendall(json.dumps(response).encode('utf-8'))
                
                # Handle execute request
                elif request.get("method") == "execute":
                    params = request.get("params", {})
                    tool = params.get("tool")
                    tool_params = params.get("parameters", {})
                    
                    result = "Tool execution failed"
                    
                    # Handle different tools
                    if tool == "get_scene_info":
                        houdini_response = houdini.send_command("get_scene_info")
                        result = json.dumps(houdini_response.get("result", {}), indent=2)
                    
                    elif tool == "create_geometry":
                        geo_type = tool_params.get("geo_type", "box")
                        houdini_response = houdini.send_command("create_geometry", {
                            "geo_type": geo_type,
                            "parent_path": "/obj"
                        })
                        if "error" in houdini_response:
                            result = f"Error creating geometry: {houdini_response['error']}"
                        else:
                            result = f"Created {geo_type} geometry at {houdini_response.get('result', {}).get('path', 'unknown')}"
                    
                    # Send response back to client
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "type": "tool_response",
                            "data": result
                        }
                    }
                    client_sock.sendall(json.dumps(response).encode('utf-8'))
                
                # Handle unknown request
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Method {request.get('method')} not found"
                        }
                    }
                    client_sock.sendall(json.dumps(response).encode('utf-8'))
            
            except Exception as e:
                print(f"Error handling request: {str(e)}", file=sys.stderr)
                try:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id") if "request" in locals() else None,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }
                    client_sock.sendall(json.dumps(error_response).encode('utf-8'))
                except:
                    pass
            finally:
                client_sock.close()
                
    except KeyboardInterrupt:
        print("Shutting down server...", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {str(e)}", file=sys.stderr)
    finally:
        server_sock.close()

if __name__ == "__main__":
    main()