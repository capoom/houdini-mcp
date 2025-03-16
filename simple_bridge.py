import json
import socket
import sys
import traceback
import time

# Simple MCP server that connects Claude to Houdini
def main():
    # Print to stderr so Claude can see the output
    print("Starting HoudiniMCP bridge with complete protocol handling...", file=sys.stderr)
    
    # Create a socket to listen for Claude's connections
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('localhost', 8080))
    server_socket.listen(1)
    
    print("Bridge listening on port 8080", file=sys.stderr)
    
    try:
        while True:
            # Accept connection from Claude
            client_socket, address = server_socket.accept()
            print(f"Received connection from {address}", file=sys.stderr)
            
            try:
                # Get message from Claude
                data = client_socket.recv(8192)
                if not data:
                    print("Empty data received", file=sys.stderr)
                    client_socket.close()
                    continue
                    
                message = data.decode('utf-8')
                print(f"Received message: {message}", file=sys.stderr)
                
                # Parse the message as JSON
                request = json.loads(message)
                request_id = request.get("id", 0)
                method = request.get("method", "")
                
                print(f"Request ID: {request_id}, Method: {method}", file=sys.stderr)
                
                # Handle initialize request
                if method == "initialize":
                    # Respond with capabilities
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "serverInfo": {
                                "name": "HoudiniMCP",
                                "version": "0.1.0"
                            },
                            "capabilities": {
                                "tools": {
                                    "create_sphere": {
                                        "description": "Create a sphere in Houdini",
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "description": "Optional name for the sphere"
                                                }
                                            }
                                        }
                                    },
                                    "get_scene_info": {
                                        "description": "Get information about the current Houdini scene"
                                    }
                                }
                            }
                        }
                    }
                    
                    # Send the response
                    response_str = json.dumps(response)
                    print(f"Sending initialize response: {response_str}", file=sys.stderr)
                    client_socket.sendall(response_str.encode('utf-8'))
                    print("Initialize response sent", file=sys.stderr)
                
                # Handle execute request
                elif method == "execute":
                    params = request.get("params", {})
                    tool = params.get("tool", "")
                    tool_params = params.get("parameters", {})
                    
                    print(f"Tool requested: {tool}", file=sys.stderr)
                    
                    result = "Command failed"
                    
                    # Create Houdini connection
                    print("Connecting to Houdini...", file=sys.stderr)
                    houdini_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    
                    try:
                        houdini_socket.connect(('localhost', 9877))
                        print("Connected to Houdini", file=sys.stderr)
                        
                        # Handle create_sphere tool
                        if tool == "create_sphere":
                            name = tool_params.get("name")
                            
                            # Build command for Houdini
                            command = {
                                "type": "create_geometry",
                                "params": {
                                    "geo_type": "sphere",
                                    "parent_path": "/obj"
                                }
                            }
                            
                            if name:
                                command["params"]["name"] = name
                            
                            # Send command to Houdini
                            command_str = json.dumps(command)
                            print(f"Sending to Houdini: {command_str}", file=sys.stderr)
                            houdini_socket.sendall(command_str.encode('utf-8'))
                            
                            # Get response from Houdini
                            houdini_response = b""
                            while True:
                                try:
                                    houdini_socket.settimeout(5.0)
                                    chunk = houdini_socket.recv(4096)
                                    if not chunk:
                                        break
                                    houdini_response += chunk
                                    
                                    # Try to parse the response
                                    try:
                                        json.loads(houdini_response.decode('utf-8'))
                                        # Valid JSON, we're done
                                        break
                                    except json.JSONDecodeError:
                                        # Not complete yet, continue receiving
                                        continue
                                except socket.timeout:
                                    print("Socket timeout waiting for Houdini", file=sys.stderr)
                                    break
                            
                            houdini_response_str = houdini_response.decode('utf-8')
                            print(f"Received from Houdini: {houdini_response_str}", file=sys.stderr)
                            
                            try:
                                houdini_data = json.loads(houdini_response_str)
                                if houdini_data.get("status") == "success":
                                    path = houdini_data.get("result", {}).get("path", "unknown")
                                    result = f"Created sphere at {path}"
                                    print(f"Success: {result}", file=sys.stderr)
                                else:
                                    error_msg = houdini_data.get("message", "Unknown error")
                                    result = f"Error: {error_msg}"
                                    print(f"Houdini error: {error_msg}", file=sys.stderr)
                            except json.JSONDecodeError:
                                result = "Error: Invalid response from Houdini"
                                print(f"Received invalid JSON from Houdini: {houdini_response_str}", file=sys.stderr)
                        
                        # Handle get_scene_info tool
                        elif tool == "get_scene_info":
                            command = {
                                "type": "get_scene_info",
                                "params": {}
                            }
                            
                            # Send command to Houdini
                            command_str = json.dumps(command)
                            print(f"Sending to Houdini: {command_str}", file=sys.stderr)
                            houdini_socket.sendall(command_str.encode('utf-8'))
                            
                            # Get response from Houdini
                            houdini_response = b""
                            while True:
                                try:
                                    houdini_socket.settimeout(5.0)
                                    chunk = houdini_socket.recv(4096)
                                    if not chunk:
                                        break
                                    houdini_response += chunk
                                    
                                    # Try to parse the response
                                    try:
                                        json.loads(houdini_response.decode('utf-8'))
                                        # Valid JSON, we're done
                                        break
                                    except json.JSONDecodeError:
                                        # Not complete yet, continue receiving
                                        continue
                                except socket.timeout:
                                    print("Socket timeout waiting for Houdini", file=sys.stderr)
                                    break
                            
                            houdini_response_str = houdini_response.decode('utf-8')
                            print(f"Received from Houdini: {houdini_response_str}", file=sys.stderr)
                            
                            try:
                                houdini_data = json.loads(houdini_response_str)
                                if houdini_data.get("status") == "success":
                                    result = json.dumps(houdini_data.get("result", {}), indent=2)
                                    print("Successfully got scene info", file=sys.stderr)
                                else:
                                    error_msg = houdini_data.get("message", "Unknown error")
                                    result = f"Error: {error_msg}"
                                    print(f"Houdini error: {error_msg}", file=sys.stderr)
                            except json.JSONDecodeError:
                                result = "Error: Invalid response from Houdini"
                                print(f"Received invalid JSON from Houdini: {houdini_response_str}", file=sys.stderr)
                        
                        # Unknown tool
                        else:
                            result = f"Unknown tool: {tool}"
                            print(f"Unknown tool requested: {tool}", file=sys.stderr)
                        
                    except Exception as e:
                        result = f"Error connecting to Houdini: {str(e)}"
                        print(f"Exception: {str(e)}", file=sys.stderr)
                        traceback.print_exc(file=sys.stderr)
                    finally:
                        try:
                            houdini_socket.close()
                        except:
                            pass
                    
                    # Send response back to Claude
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "type": "tool_response",
                            "data": result
                        }
                    }
                    
                    response_str = json.dumps(response)
                    print(f"Sending response to Claude: {response_str}", file=sys.stderr)
                    client_socket.sendall(response_str.encode('utf-8'))
                    print("Response sent to Claude", file=sys.stderr)
                
                # Handle shutdown request
                elif method == "shutdown":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": None
                    }
                    
                    client_socket.sendall(json.dumps(response).encode('utf-8'))
                    print("Shutdown request received, shutting down server", file=sys.stderr)
                    break
                
                # Unknown method
                else:
                    print(f"Unknown method: {method}", file=sys.stderr)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                    
                    client_socket.sendall(json.dumps(response).encode('utf-8'))
                
            except Exception as e:
                print(f"Error handling request: {str(e)}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                
                # Send error response if possible
                try:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id if 'request_id' in locals() else None,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }
                    
                    client_socket.sendall(json.dumps(error_response).encode('utf-8'))
                except:
                    pass
            finally:
                # Close the client socket
                try:
                    client_socket.close()
                except:
                    pass
                
    except KeyboardInterrupt:
        print("Server stopped by user", file=sys.stderr)
    finally:
        server_socket.close()
        print("Server shut down", file=sys.stderr)

if __name__ == "__main__":
    main()