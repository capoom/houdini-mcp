import json
import sys
import socket

def main():
    # MCP servers should use stdin/stdout for communication
    while True:
        # Read a line from standard input
        line = sys.stdin.readline()
        if not line:
            break
            
        try:
            # Parse the JSON request
            request = json.loads(line)
            
            # Handle initialize request
            if request.get("method") == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "minimal-houdini-mcp", "version": "0.1.0"},
                        "capabilities": {
                            "tools": {
                                "create_sphere": {
                                    "description": "Create a sphere in Houdini"
                                }
                            }
                        }
                    }
                }
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
            # Handle execute request
            elif request.get("method") == "execute":
                tool = request.get("params", {}).get("tool")
                
                if tool == "create_sphere":
                    # Connect to Houdini
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        sock.connect(('localhost', 9877))
                        
                        # Send command to create sphere
                        command = {"type": "create_geometry", "params": {"geo_type": "sphere", "parent_path": "/obj"}}
                        sock.sendall(json.dumps(command).encode('utf-8'))
                        
                        # Get response from Houdini
                        response_data = sock.recv(4096)
                        houdini_response = json.loads(response_data.decode('utf-8'))
                        
                        if houdini_response.get("status") == "success":
                            sphere_path = houdini_response.get("result", {}).get("path", "unknown")
                            result = f"Created sphere at {sphere_path}"
                        else:
                            result = f"Error: {houdini_response.get('message', 'Unknown error')}"
                    except Exception as e:
                        result = f"Error connecting to Houdini: {str(e)}"
                    finally:
                        sock.close()
                    
                    # Send response to Claude
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "type": "tool_response",
                            "data": result
                        }
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                    
        except Exception as e:
            # Handle errors
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if "request" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()