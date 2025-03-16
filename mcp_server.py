"""Standalone MCP Server for Houdini"""

import socket
import json
import time
import logging
import sys
from typing import Dict, Any, Optional, List
import subprocess
from threading import Thread

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StandaloneHoudiniMCP")

class HoudiniConnection:
    def __init__(self, host='localhost', port=9877):
        self.host = host
        self.port = port
        self.sock = None
        
    def connect(self) -> bool:
        """Connect to the Houdini addon socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Houdini at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Houdini: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Houdini addon"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Houdini: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        sock.settimeout(15.0)  # Socket timeout
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        if not chunks:
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    logger.warning("Socket timeout during chunked receive")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise
        except socket.timeout:
            logger.warning("Socket timeout during chunked receive")
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # If we get here, we either timed out or broke out of the loop
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                # Try to parse what we have
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Houdini and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Houdini")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            # Log the command being sent
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # Set a timeout for receiving
            self.sock.settimeout(15.0)
            
            # Receive the response using the improved receive_full_response method
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"Houdini error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Houdini"))
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Houdini")
            self.sock = None
            raise Exception("Timeout waiting for Houdini response - try simplifying your request")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Houdini lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Houdini: {str(e)}")
            # Try to log what was received
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            raise Exception(f"Invalid response from Houdini: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Houdini: {str(e)}")
            self.sock = None
            raise Exception(f"Communication error with Houdini: {str(e)}")

# Global connection instance
_houdini_connection = None

def get_houdini_connection():
    """Get or create a persistent Houdini connection"""
    global _houdini_connection
    
    # If we have an existing connection, check if it's still valid
    if _houdini_connection is not None:
        try:
            # Test connection with a simple info request
            _houdini_connection.send_command("get_scene_info")
            return _houdini_connection
        except Exception as e:
            # Connection is dead, close it and create a new one
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _houdini_connection.disconnect()
            except:
                pass
            _houdini_connection = None
    
    # Create a new connection if needed
    if _houdini_connection is None:
        _houdini_connection = HoudiniConnection(host="localhost", port=9877)
        if not _houdini_connection.connect():
            logger.error("Failed to connect to Houdini")
            _houdini_connection = None
            raise Exception("Could not connect to Houdini. Make sure the Houdini addon is running.")
        logger.info("Created new persistent connection to Houdini")
    
    return _houdini_connection

def simple_mcp_server():
    """Run a simple MCP server for testing"""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('localhost', 8080))
        server_socket.listen(1)
        
        print("MCP Server listening on localhost:8080")
        print("Connect Claude Desktop to this server to interact with Houdini")
        print("Press Ctrl+C to stop the server")
        
        while True:
            client_socket, address = server_socket.accept()
            print(f"Connection from {address}")
            
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                client_socket.close()
                continue
            
            print(f"Received from Claude: {data}")
            
            # Parse the MCP request
            try:
                request = json.loads(data)
                command = request.get("command", "")
                payload = request.get("payload", {})
                
                # Handle the request
                if command == "execute":
                    tool_name = payload.get("tool", "")
                    tool_params = payload.get("parameters", {})
                    
                    response_data = {"status": "success", "result": ""}
                    
                    try:
                        # Process different tools
                        if tool_name == "get_scene_info":
                            houdini = get_houdini_connection()
                            result = houdini.send_command("get_scene_info")
                            response_data["result"] = json.dumps(result, indent=2)
                            
                        elif tool_name == "create_geometry":
                            houdini = get_houdini_connection()
                            params = {
                                "geo_type": tool_params.get("geo_type", "box"),
                                "parent_path": tool_params.get("parent_path", "/obj")
                            }
                            if "name" in tool_params:
                                params["name"] = tool_params["name"]
                            if "position" in tool_params:
                                params["position"] = tool_params["position"]
                            if "parameters" in tool_params:
                                params["parameters"] = tool_params["parameters"]
                                
                            result = houdini.send_command("create_geometry", params)
                            
                            if "error" in result:
                                response_data["result"] = f"Error creating geometry: {result['error']}"
                            else:
                                response_data["result"] = f"Created {params['geo_type']} geometry at {result['path']}"
                        
                        elif tool_name == "set_material":
                            houdini = get_houdini_connection()
                            params = {
                                "node_path": tool_params.get("node_path", ""),
                                "material_type": tool_params.get("material_type", "principledshader")
                            }
                            if "material_name" in tool_params:
                                params["material_name"] = tool_params["material_name"]
                            if "parameters" in tool_params:
                                params["parameters"] = tool_params["parameters"]
                                
                            result = houdini.send_command("set_material", params)
                            
                            if "error" in result:
                                response_data["result"] = f"Error setting material: {result['error']}"
                            else:
                                response_data["result"] = f"Applied {params['material_type']} material to {params['node_path']}"
                        
                        elif tool_name == "execute_houdini_code":
                            houdini = get_houdini_connection()
                            code = tool_params.get("code", "")
                            result = houdini.send_command("execute_code", {"code": code})
                            
                            if "error" in result:
                                response_data["result"] = f"Error executing code: {result['error']}"
                            else:
                                response_data["result"] = "Code executed successfully in Houdini"
                        
                        else:
                            response_data = {
                                "status": "error", 
                                "result": f"Unknown tool: {tool_name}"
                            }
                    
                    except Exception as e:
                        response_data = {
                            "status": "error", 
                            "result": f"Error executing tool: {str(e)}"
                        }
                        
                else:
                    response_data = {
                        "status": "error", 
                        "result": f"Unknown command: {command}"
                    }
                
                # Send the response back to Claude
                response = {
                    "type": "tool_response",
                    "data": response_data["result"]
                }
                
                client_socket.sendall(json.dumps(response).encode('utf-8'))
                print(f"Sent response: {response}")
                
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {data}")
                error_response = {
                    "type": "error",
                    "data": "Invalid JSON request"
                }
                client_socket.sendall(json.dumps(error_response).encode('utf-8'))
            
            client_socket.close()
            
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        if 'server_socket' in locals():
            server_socket.close()
        if _houdini_connection:
            _houdini_connection.disconnect()

if __name__ == "__main__":
    simple_mcp_server()
