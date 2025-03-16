import hou
import json
import socket
import threading
import time
import traceback
from typing import Dict, Any, Optional, Tuple, List

class HoudiniMCPServer:
    def __init__(self, host='localhost', port=9877):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.client = None
        self.buffer = b''  # Buffer for incomplete data
        self.thread = None
    
    def start(self):
        """Start the Houdini MCP server"""
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            
            # Start server in a separate thread
            self.thread = threading.Thread(target=self._run_server)
            self.thread.daemon = True
            self.thread.start()
            
            print(f"HoudiniMCP server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to start server: {str(e)}")
            self.stop()
            return False
            
    def stop(self):
        """Stop the Houdini MCP server"""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            
        if self.socket:
            self.socket.close()
        if self.client:
            self.client.close()
            
        self.socket = None
        self.client = None
        print("HoudiniMCP server stopped")
    
    def _run_server(self):
        """Main server loop"""
        self.socket.settimeout(0.5)  # Use a timeout for checking running state
        
        while self.running:
            try:
                # Accept new connections
                if not self.client:
                    try:
                        self.client, address = self.socket.accept()
                        print(f"Connected to client: {address}")
                    except socket.timeout:
                        continue  # No connection waiting
                    except Exception as e:
                        print(f"Error accepting connection: {str(e)}")
                        continue
                
                # Process existing connection
                if self.client:
                    try:
                        self.client.settimeout(0.5)  # Small timeout for recv
                        try:
                            data = self.client.recv(8192)
                            if data:
                                self.buffer += data
                                # Try to process complete messages
                                try:
                                    # Attempt to parse the buffer as JSON
                                    command = json.loads(self.buffer.decode('utf-8'))
                                    # If successful, clear the buffer and process command
                                    self.buffer = b''
                                    response = self.execute_command(command)
                                    response_json = json.dumps(response)
                                    self.client.sendall(response_json.encode('utf-8'))
                                except json.JSONDecodeError:
                                    # Incomplete data, keep in buffer
                                    pass
                            else:
                                # Connection closed by client
                                print("Client disconnected")
                                self.client.close()
                                self.client = None
                                self.buffer = b''
                        except socket.timeout:
                            pass  # No data available
                        except Exception as e:
                            print(f"Error receiving data: {str(e)}")
                            self.client.close()
                            self.client = None
                            self.buffer = b''
                    except Exception as e:
                        print(f"Error with client: {str(e)}")
                        if self.client:
                            self.client.close()
                            self.client = None
                        self.buffer = b''
            except Exception as e:
                print(f"Server error: {str(e)}")
        
        print("Server loop exited")

    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command from the client"""
        try:
            cmd_type = command.get("type")
            params = command.get("params", {})
            
            # Register all command handlers
            handlers = {
                "get_scene_info": self.get_scene_info,
                "create_node": self.create_node,
                "modify_node": self.modify_node,
                "delete_node": self.delete_node,
                "get_node_info": self.get_node_info,
                "execute_code": self.execute_code,
                "set_parameter": self.set_parameter,
                "create_geometry": self.create_geometry,
                "layout_network": self.layout_network,
                "connect_nodes": self.connect_nodes,
                "set_material": self.set_material,
                "create_subnet": self.create_subnet,
                "create_digital_asset": self.create_digital_asset,
                "get_parameter_info": self.get_parameter_info,
                "save_hip": self.save_hip,
                "load_hip": self.load_hip,
                "create_camera": self.create_camera,
                "create_light": self.create_light,
                "create_sim": self.create_sim,
                "run_simulation": self.run_simulation,
                "export_fbx": self.export_fbx,
                "export_abc": self.export_abc,
                "export_usd": self.export_usd,
                "render_scene": self.render_scene,
            }
            
            handler = handlers.get(cmd_type)
            if handler:
                try:
                    print(f"Executing handler for {cmd_type}")
                    result = handler(**params)
                    print(f"Handler execution complete")
                    return {"status": "success", "result": result}
                except Exception as e:
                    print(f"Error in handler: {str(e)}")
                    traceback.print_exc()
                    return {"status": "error", "message": str(e)}
            else:
                return {"status": "error", "message": f"Unknown command type: {cmd_type}"}
        except Exception as e:
            print(f"Error executing command: {str(e)}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current Houdini scene"""
        try:
            # Basic scene info
            scene_info = {
                "hip_file": hou.hipFile.path(),
                "name": hou.hipFile.basename(),
                "modified": hou.hipFile.isModified(),
                "fps": hou.fps(),
                "frame_range": [hou.playbar.frameRange()],
                "current_frame": hou.frame(),
                "node_count": len(hou.node("/").allSubChildren()),
                "top_level_nodes": []
            }
            
            # Get top-level nodes
            for node in hou.node("/").children():
                node_info = {
                    "name": node.name(),
                    "type": node.type().name(),
                    "path": node.path(),
                    "child_count": len(node.allSubChildren()),
                }
                scene_info["top_level_nodes"].append(node_info)
            
            return scene_info
        except Exception as e:
            print(f"Error in get_scene_info: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def get_node_info(self, path: str) -> Dict[str, Any]:
        """Get detailed information about a specific node"""
        try:
            node = hou.node(path)
            if not node:
                raise ValueError(f"Node not found: {path}")
            
            # Basic node info
            node_info = {
                "name": node.name(),
                "type": node.type().name(),
                "category": node.type().category().name(),
                "path": node.path(),
                "is_bypassed": node.isBypassed(),
                "is_displayed": node.isDisplayFlagSet(),
                "is_render_flagged": node.isRenderFlagSet(),
                "is_selectable": node.isSelectableInViewport(), 
                "position": [node.position()[0], node.position()[1]],
                "color": list(node.color()) if node.color() else None,
                "has_errors": node.errors() != "",
                "errors": node.errors(),
                "child_count": len(node.children()),
                "children": [child.name() for child in node.children()],
                "parameter_count": len(node.parms()),
                "parameters": {},
                "inputs": [input_node.path() if input_node else None for input_node in node.inputs()],
                "outputs": [output_node.path() if output_node else None for output_node in node.outputs()],
            }
            
            # Add parameter info (limit to avoid overwhelming response)
            for i, parm in enumerate(node.parms()):
                if i >= 25:  # Limit to first 25 parameters
                    break
                node_info["parameters"][parm.name()] = {
                    "value": self._get_parameter_value(parm),
                    "label": parm.description(),
                    "type": parm.parmTemplate().type().name(),
                }
            
            # Add more specific info for different node types
            if node.type().category().name() == "Sop":  # Geometry nodes
                geo = node.geometry()
                if geo:
                    node_info["geometry"] = {
                        "point_count": geo.intrinsicValue("pointcount"),
                        "prim_count": geo.intrinsicValue("primitivecount"),
                        "vertex_count": geo.intrinsicValue("vertexcount"),
                        "bounds": list(geo.boundingBox().sizes()),
                    }
            
            return node_info
        except Exception as e:
            print(f"Error in get_node_info: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def _get_parameter_value(self, parm):
        """Helper to get parameter value in a JSON-serializable format"""
        try:
            parm_type = parm.parmTemplate().type()
            
            if parm_type == hou.parmTemplateType.Float:
                return parm.eval()
            elif parm_type == hou.parmTemplateType.Int:
                return parm.eval()
            elif parm_type == hou.parmTemplateType.String:
                return parm.eval()
            elif parm_type == hou.parmTemplateType.Toggle:
                return bool(parm.eval())
            elif parm_type == hou.parmTemplateType.Menu:
                return parm.eval()
            elif parm_type == hou.parmTemplateType.FloatVector:
                return list(parm.eval())
            elif parm_type == hou.parmTemplateType.IntVector:
                return list(parm.eval())
            elif parm_type == hou.parmTemplateType.Color:
                return list(parm.eval())
            else:
                # For complex types, convert to string
                return str(parm.eval())
        except:
            return "error getting value"
    
    def create_node(self, 
                   parent_path: str, 
                   node_type: str, 
                   node_name: Optional[str] = None,
                   position: Optional[List[float]] = None) -> Dict[str, Any]:
        """Create a new node in the network"""
        try:
            parent = hou.node(parent_path)
            if not parent:
                raise ValueError(f"Parent node not found: {parent_path}")
            
            # Create the node
            new_node = parent.createNode(node_type, node_name)
            
            # Set position if provided
            if position and len(position) == 2:
                new_node.setPosition((position[0], position[1]))
            
            # Special handling for specific node types
            category = new_node.type().category().name()
            
            # For SOPs, set display flag
            if category == "Sop":
                new_node.setDisplayFlag(True)
                new_node.setRenderFlag(True)
            
            return {
                "path": new_node.path(),
                "name": new_node.name(),
                "type": new_node.type().name(),
                "category": category,
                "position": [new_node.position()[0], new_node.position()[1]]
            }
        except Exception as e:
            print(f"Error in create_node: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def modify_node(self, 
                   path: str, 
                   position: Optional[List[float]] = None,
                   color: Optional[List[float]] = None,
                   name: Optional[str] = None,
                   bypass: Optional[bool] = None,
                   display: Optional[bool] = None) -> Dict[str, Any]:
        """Modify an existing node"""
        try:
            node = hou.node(path)
            if not node:
                raise ValueError(f"Node not found: {path}")
            
            # Apply changes
            if position and len(position) == 2:
                node.setPosition((position[0], position[1]))
                
            if color and len(color) >= 3:
                # Convert RGB to Houdini color
                alpha = 1.0 if len(color) < 4 else color[3]
                node.setColor(hou.Color((color[0], color[1], color[2], alpha)))
                
            if name:
                node.setName(name)
                
            if bypass is not None:
                node.bypass(bypass)
                
            if display is not None:
                node.setDisplayFlag(display)
                if display:
                    node.setRenderFlag(True)
            
            return {
                "path": node.path(),
                "name": node.name(),
                "position": [node.position()[0], node.position()[1]],
                "color": list(node.color()) if node.color() else None,
                "is_bypassed": node.isBypassed(),
                "is_displayed": node.isDisplayFlagSet()
            }
        except Exception as e:
            print(f"Error in modify_node: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def delete_node(self, path: str) -> Dict[str, Any]:
        """Delete a node from the network"""
        try:
            node = hou.node(path)
            if not node:
                raise ValueError(f"Node not found: {path}")
            
            node_name = node.name()
            node_path = node.path()
            
            # Delete the node
            node.destroy()
            
            return {
                "deleted": True,
                "name": node_name,
                "path": node_path
            }
        except Exception as e:
            print(f"Error in delete_node: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def execute_code(self, code: str) -> Dict[str, Any]:
        """Execute arbitrary Python code in Houdini"""
        try:
            # Create a local namespace for execution
            namespace = {"hou": hou}
            exec(code, namespace)
            return {"executed": True}
        except Exception as e:
            print(f"Error in execute_code: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def set_parameter(self, 
                      node_path: str, 
                      parameter_name: str, 
                      value: Any) -> Dict[str, Any]:
        """Set a parameter value on a node"""
        try:
            node = hou.node(node_path)
            if not node:
                raise ValueError(f"Node not found: {node_path}")
            
            parm = node.parm(parameter_name)
            if not parm:
                # Try to find in vector parms (e.g. 'tx' might be part of 't')
                parm = node.parmTuple(parameter_name)
                if not parm:
                    raise ValueError(f"Parameter not found: {parameter_name}")
            
            # Set the parameter value
            if isinstance(parm, hou.Parm):
                parm.set(value)
            elif isinstance(parm, hou.ParmTuple):
                # For vector parms, ensure value is a list of correct length
                if not isinstance(value, list):
                    value = [value] * len(parm)
                elif len(value) != len(parm):
                    value = value[:len(parm)] + [value[-1]] * (len(parm) - len(value))
                parm.set(value)
            
            return {
                "node": node_path,
                "parameter": parameter_name,
                "value": value
            }
        except Exception as e:
            print(f"Error in set_parameter: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def create_geometry(self, 
                       parent_path: str,
                       geo_type: str = "box",
                       name: Optional[str] = None,
                       position: Optional[List[float]] = None,
                       parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a geometry node with the specified type"""
        try:
            parent = hou.node(parent_path)
            if not parent:
                raise ValueError(f"Parent node not found: {parent_path}")
            
            # Create a geometry container if parent is not a SOP context
            if parent.type().category().name() != "Sop":
                # Find or create the geo node
                geo_container = None
                container_name = name + "_container" if name else "geo1"
                
                for child in parent.children():
                    if child.type().name() == "geo" and (not name or name in child.name()):
                        geo_container = child
                        break
                
                if not geo_container:
                    geo_container = parent.createNode("geo", container_name)
                    if position:
                        geo_container.setPosition((position[0], position[1]))
                
                # Set parent to the container
                parent = geo_container
            
            # Map common geo types to Houdini node types
            geo_type_map = {
                "box": "box",
                "sphere": "sphere",
                "torus": "torus",
                "grid": "grid",
                "tube": "tube",
                "circle": "circle",
                "curve": "curve",
                "line": "line",
                "platonic": "platonic",
                "cylinder": "tube"  # Map cylinder to tube
            }
            
            # Default to box if type not recognized
            houdini_type = geo_type_map.get(geo_type.lower(), "box")
            
            # Create the geometry node
            geo_node = parent.createNode(houdini_type, name)
            
            # Set position if provided
            if position and len(position) == 2:
                geo_node.setPosition((position[0], position[1]))
                
            # Set parameters if provided
            if parameters:
                for param_name, param_value in parameters.items():
                    try:
                        parm = geo_node.parm(param_name)
                        if parm:
                            parm.set(param_value)
                        else:
                            # Try as vector parm
                            parm_tuple = geo_node.parmTuple(param_name)
                            if parm_tuple:
                                if isinstance(param_value, list):
                                    parm_tuple.set(param_value)
                                else:
                                    parm_tuple.set([param_value] * len(parm_tuple))
                    except Exception as e:
                        print(f"Error setting parameter {param_name}: {str(e)}")
            
            # Set display flag
            geo_node.setDisplayFlag(True)
            geo_node.setRenderFlag(True)
            
            return {
                "path": geo_node.path(),
                "name": geo_node.name(),
                "type": geo_node.type().name(),
                "category": geo_node.type().category().name(),
                "position": [geo_node.position()[0], geo_node.position()[1]],
                "parent": parent.path()
            }
        except Exception as e:
            print(f"Error in create_geometry: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def layout_network(self, path: str, auto_layout: bool = True) -> Dict[str, Any]:
        """Layout nodes in a network"""
        try:
            network = hou.node(path)
            if not network:
                raise ValueError(f"Network not found: {path}")
            
            if auto_layout:
                # Use Houdini's automatic layout
                network.layoutChildren()
            
            return {
                "success": True,
                "path": network.path(),
                "name": network.name()
            }
        except Exception as e:
            print(f"Error in layout_network: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def connect_nodes(self, 
                     from_path: str, 
                     to_path: str,
                     from_output: int = 0,
                     to_input: int = 0) -> Dict[str, Any]:
        """Connect two nodes together"""
        try:
            from_node = hou.node(from_path)
            if not from_node:
                raise ValueError(f"Source node not found: {from_path}")
                
            to_node = hou.node(to_path)
            if not to_node:
                raise ValueError(f"Destination node not found: {to_path}")
            
            # Connect the nodes
            to_node.setInput(to_input, from_node, from_output)
            
            return {
                "success": True,
                "from": from_path,
                "to": to_path,
                "from_output": from_output,
                "to_input": to_input
            }
        except Exception as e:
            print(f"Error in connect_nodes: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def set_material(self, 
                    node_path: str, 
                    material_type: str = "principledshader",
                    material_name: Optional[str] = None,
                    parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create and apply a material to a node"""
        try:
            # Get the target node
            target_node = hou.node(node_path)
            if not target_node:
                raise ValueError(f"Node not found: {node_path}")
            
            # Find or create a material network
            mat_context = hou.node("/mat")
            if not mat_context:
                # Create the material context if it doesn't exist
                mat_context = hou.node("/").createNode("mat")
            
            # Create the material
            if not material_name:
                material_name = f"{target_node.name()}_material"
            
            # Check if the material already exists
            existing_mat = None
            for node in mat_context.children():
                if node.name() == material_name:
                    existing_mat = node
                    break
            
            # Create or use existing material
            if existing_mat:
                material = existing_mat
            else:
                material = mat_context.createNode(material_type, material_name)
            
            # Set material parameters if provided
            if parameters:
                for param_name, param_value in parameters.items():
                    try:
                        parm = material.parm(param_name)
                        if parm:
                            parm.set(param_value)
                        else:
                            # Try as vector parm
                            parm_tuple = material.parmTuple(param_name)
                            if parm_tuple:
                                if isinstance(param_value, list):
                                    parm_tuple.set(param_value)
                                else:
                                    parm_tuple.set([param_value] * len(parm_tuple))
                    except Exception as e:
                        print(f"Error setting material parameter {param_name}: {str(e)}")
            
            # Apply the material to the target node
            if target_node.type().category().name() == "Sop":
                # For geometry nodes, set the shop_materialpath parameter
                material_path = material.path()
                mat_parm = target_node.parm("shop_materialpath")
                if mat_parm:
                    mat_parm.set(material_path)
                else:
                    # If no material parameter, try to create a material SOP
                    try:
                        material_sop = target_node.createNode("material")
                        material_sop.parm("shop_materialpath1").set(material_path)
                        
                        # Connect to the end of the chain if possible
                        displayed = None
                        for node in target_node.children():
                            if node.isDisplayFlagSet():
                                displayed = node
                                break
                        
                        if displayed:
                            material_sop.setInput(0, displayed)
                            material_sop.setDisplayFlag(True)
                            material_sop.setRenderFlag(True)
                            displayed.setDisplayFlag(False)
                            displayed.setRenderFlag(False)
                    except Exception as me:
                        print(f"Error creating material SOP: {str(me)}")
            
            return {
                "success": True,
                "node": node_path,
                "material": material.path(),
                "material_name": material.name(),
                "material_type": material.type().name()
            }
        except Exception as e:
            print(f"Error in set_material: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def create_subnet(self, 
                     parent_path: str,
                     name: Optional[str] = None,
                     position: Optional[List[float]] = None,
                     node_type: str = "subnet") -> Dict[str, Any]:
        """Create a subnet node"""
        try:
            parent = hou.node(parent_path)
            if not parent:
                raise ValueError(f"Parent node not found: {parent_path}")
            
            # Create the subnet
            subnet = parent.createNode(node_type, name)
            
            # Set position if provided
            if position and len(position) == 2:
                subnet.setPosition((position[0], position[1]))
            
            return {
                "path": subnet.path(),
                "name": subnet.name(),
                "type": subnet.type().name(),
                "category": subnet.type().category().name(),
                "position": [subnet.position()[0], subnet.position()[1]]
            }
        except Exception as e:
            print(f"Error in create_subnet: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def create_digital_asset(self, 
                           node_path: str,
                           name: str,
                           label: Optional[str] = None,
                           save_path: Optional[str] = None) -> Dict[str, Any]:
        """Create a digital asset from a node"""
        try:
            node = hou.node(node_path)
            if not node:
                raise ValueError(f"Node not found: {node_path}")
            
            # Generate save path if not provided
            if not save_path:
                temp_dir = hou.expandString("$TEMP")
                save_path = f"{temp_dir}/{name}.hda"
            
            # Set label if not provided
            if not label:
                label = name.replace("_", " ").title()
            
            # Create the digital asset
            asset_type_name = f"{name}::1.0"
            hda_node = node.createDigitalAsset(
                name=name,
                hda_file_name=save_path,
                description=f"Created by HoudiniMCP",
                min_num_inputs=node.minInputs(),
                max_num_inputs=node.maxInputs(),
                version="1.0",
                save_as_embedded=False
            )
            
            # Set the label
            hda_def = hda_node.type().definition()
            if hda_def:
                hda_def.setLabel(label)
                hda_def.save()
            
            return {
                "success": True,
                "path": hda_node.path(),
                "name": hda_node.name(),
                "type": hda_node.type().name(),
                "hda_file": save_path
            }
        except Exception as e:
            print(f"Error in create_digital_asset: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def get_parameter_info(self, node_path: str, parameter_name: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed parameter information for a node"""
        try:
            node = hou.node(node_path)
            if not node:
                raise ValueError(f"Node not found: {node_path}")
            
            # If a specific parameter is requested
            if parameter_name:
                parm = node.parm(parameter_name)
                if parm:
                    return {
                        "name": parm.name(),
                        "label": parm.description(),
                        "type": parm.parmTemplate().type().name(),
                        "value": self._get_parameter_value(parm),
                        "is_vector": False
                    }
                
                # Try as vector parameter
                parm_tuple = node.parmTuple(parameter_name)
                if parm_tuple:
                    return {
                        "name": parm_tuple.name(),
                        "label": parm_tuple.description(),
                        "type": parm_tuple.parmTemplate().type().name(),
                        "value": [self._get_parameter_value(p) for p in parm_tuple],
                        "is_vector": True,
                        "components": [p.name() for p in parm_tuple]
                    }
                
                raise ValueError(f"Parameter not found: {parameter_name}")
            
            # If all parameters are requested
            result = {
                "node": node_path,
                "parameters": {}
            }
            
            # Include all parameters
            for parm in node.parms():
                result["parameters"][parm.name()] = {
                    "label": parm.description(),
                    "type": parm.parmTemplate().type().name(),
                    "value": self._get_parameter_value(parm)
                }
            
            return result
        except Exception as e:
            print(f"Error in get_parameter_info: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def save_hip(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Save the current Houdini scene"""
        try:
            if not file_path:
                # Use current hip file path
                file_path = hou.hipFile.path()
                
                # If it's untitled, save to temp
                if not file_path or file_path == "untitled.hip":
                    temp_dir = hou.expandString("$TEMP")
                    file_path = f"{temp_dir}/houdinimcp_save.hip"
            
            # Ensure the path has a .hip extension
            if not file_path.endswith((".hip", ".hipnc", ".hiplc")):
                file_path += ".hip"
            
            # Save the file
            hou.hipFile.save(file_path)
            
            return {
                "success": True,
                "file_path": file_path,
                "name": hou.hipFile.basename()
            }
        except Exception as e:
            print(f"Error in save_hip: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def load_hip(self, file_path: str) -> Dict[str, Any]:
        """Load a Houdini scene file"""
        try:
            # Check if the current scene has unsaved changes
            if hou.hipFile.hasUnsavedChanges():
                # Save to a temporary file
                temp_dir = hou.expandString("$TEMP")
                backup_path = f"{temp_dir}/houdinimcp_backup.hip"
                hou.hipFile.save(backup_path)
            
            # Load the file
            hou.hipFile.load(file_path)
            
            return {
                "success": True,
                "file_path": file_path,
                "name": hou.hipFile.basename()
            }
        except Exception as e:
            print(f"Error in load_hip: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def create_camera(self, 
                     parent_path: str = "/obj",
                     name: Optional[str] = None,
                     position: Optional[List[float]] = None,
                     look_at: Optional[List[float]] = None) -> Dict[str, Any]:
        """Create a camera with optional positioning"""
        try:
            parent = hou.node(parent_path)
            if not parent:
                raise ValueError(f"Parent node not found: {parent_path}")
            
            # Create the camera
            camera = parent.createNode("cam", name)
            
            # Set position if provided
            if position and len(position) == 3:
                camera.parmTuple("t").set(position)
            
            # Set look-at target if provided
            if look_at and len(look_at) == 3:
                # Calculate rotation to look at the target
                try:
                    from_pos = hou.Vector3(camera.evalParmTuple("t"))
                    to_pos = hou.Vector3(look_at)
                    
                    # Create a rotation that points to the target
                    direction = to_pos - from_pos
                    rotation = hou.Vector3(0, 0, 0)
                    
                    # Calculate rotations
                    # X-axis rotation (pitch)
                    rotation[0] = -math.atan2(direction[1], math.sqrt(direction[0]**2 + direction[2]**2))
                    # Y-axis rotation (yaw)
                    rotation[1] = math.atan2(direction[0], direction[2])
                    
                    # Convert to degrees
                    rotation = hou.Vector3([math.degrees(angle) for angle in rotation])
                    
                    # Set rotation parameters
                    camera.parmTuple("r").set(rotation)
                except:
                    # If look-at calculation fails, just set the look_at parameter if available
                    look_at_parm = camera.parmTuple("lookat")
                    if look_at_parm:
                        look_at_parm.set(look_at)
            
            return {
                "path": camera.path(),
                "name": camera.name(),
                "type": camera.type().name(),
                "position": list(camera.evalParmTuple("t")),
                "rotation": list(camera.evalParmTuple("r"))
            }
        except Exception as e:
            print(f"Error in create_camera: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def create_light(self, 
                    parent_path: str = "/obj",
                    light_type: str = "hlight",
                    name: Optional[str] = None,
                    position: Optional[List[float]] = None,
                    parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a light of the specified type"""
        try:
            parent = hou.node(parent_path)
            if not parent:
                raise ValueError(f"Parent node not found: {parent_path}")
            
            # Map light types to Houdini node types
            light_type_map = {
                "point": "hlight", 
                "spot": "hlight",
                "directional": "hlight",
                "area": "hlight",
                "environment": "envlight"
            }
            
            # Default to hlight if type not recognized
            houdini_type = light_type_map.get(light_type.lower(), light_type.lower())
            
            # Create the light
            light = parent.createNode(houdini_type, name)
            
            # Set position if provided
            if position and len(position) == 3:
                light.parmTuple("t").set(position)
            
            # Set light type for hlights
            if houdini_type == "hlight" and light_type.lower() in ["point", "spot", "directional", "area"]:
                light_type_parm = light.parm("light_type")
                if light_type_parm:
                    light_type_map_values = {
                        "point": 0,
                        "spot": 1,
                        "directional": 2,
                        "area": 3
                    }
                    light_type_parm.set(light_type_map_values.get(light_type.lower(), 0))
            
            # Set parameters if provided
            if parameters:
                for param_name, param_value in parameters.items():
                    try:
                        parm = light.parm(param_name)
                        if parm:
                            parm.set(param_value)
                        else:
                            # Try as vector parm
                            parm_tuple = light.parmTuple(param_name)
                            if parm_tuple:
                                if isinstance(param_value, list):
                                    parm_tuple.set(param_value)
                                else:
                                    parm_tuple.set([param_value] * len(parm_tuple))
                    except Exception as e:
                        print(f"Error setting light parameter {param_name}: {str(e)}")
            
            return {
                "path": light.path(),
                "name": light.name(),
                "type": light.type().name(),
                "light_type": light_type.lower(),
                "position": list(light.evalParmTuple("t"))
            }
        except Exception as e:
            print(f"Error in create_light: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def create_sim(self, 
                  sim_type: str,
                  parent_path: str = "/obj",
                  name: Optional[str] = None,
                  position: Optional[List[float]] = None) -> Dict[str, Any]:
        """Create a simulation network of the specified type"""
        try:
            parent = hou.node(parent_path)
            if not parent:
                raise ValueError(f"Parent node not found: {parent_path}")
            
            # Map simulation types to Houdini node types
            sim_type_map = {
                "pyro": "dopnet",
                "fluid": "dopnet",
                "cloth": "dopnet",
                "rigid": "dopnet",
                "wire": "dopnet",
                "grains": "dopnet",
                "flip": "dopnet",
                "popnet": "popnet",
                "particles": "popnet",
                "crowd": "crowdsim"
            }
            
            # Default to dopnet if type not recognized
            houdini_type = sim_type_map.get(sim_type.lower(), "dopnet")
            
            # Create the simulation network
            if not name:
                name = f"{sim_type.lower()}_sim"
            
            sim_node = parent.createNode(houdini_type, name)
            
            # Set position if provided
            if position and len(position) == 2:
                sim_node.setPosition((position[0], position[1]))
            
            # Special setup for different sim types
            if sim_type.lower() == "pyro":
                # Try to set up a pyro simulation
                try:
                    # Execute the shelf tool or create basic setup
                    shelf_tool = hou.shelves.tools().get("shelf_pyro_setupsim")
                    if shelf_tool:
                        shelf_tool.execute()
                    else:
                        # Basic setup - create source
                        geo = parent.createNode("geo", f"{name}_source")
                        geo.setPosition((sim_node.position()[0] - 3, sim_node.position()[1]))
                        
                        # Create a sphere as emission source
                        sphere = geo.createNode("sphere")
                        sphere.setDisplayFlag(True)
                        sphere.setRenderFlag(True)
                except Exception as setup_error:
                    print(f"Error setting up pyro sim: {str(setup_error)}")
            
            elif sim_type.lower() == "flip":
                # Try to set up a FLIP simulation
                try:
                    shelf_tool = hou.shelves.tools().get("shelf_fluids_setupsim")
                    if shelf_tool:
                        shelf_tool.execute()
                    else:
                        # Basic setup
                        geo = parent.createNode("geo", f"{name}_source")
                        geo.setPosition((sim_node.position()[0] - 3, sim_node.position()[1]))
                        
                        # Create a container
                        box = geo.createNode("box")
                        box.setDisplayFlag(True)
                        box.setRenderFlag(True)
                except Exception as setup_error:
                    print(f"Error setting up FLIP sim: {str(setup_error)}")
            
            elif sim_type.lower() == "particles" or houdini_type == "popnet":
                # Try to set up a particle simulation
                try:
                    if sim_node.type().name() == "popnet":
                        # Basic POP setup
                        source = sim_node.createNode("popnet_source")
                        source.setPosition((0, 0))
                        
                        location = sim_node.createNode("popnet_location")
                        location.setPosition((0, -2))
                        
                        # Connect them
                        location.setInput(0, source)
                        
                        # Set defaults
                        location.setDisplayFlag(True)
                        location.setRenderFlag(True)
                except Exception as setup_error:
                    print(f"Error setting up particle sim: {str(setup_error)}")
            
            return {
                "path": sim_node.path(),
                "name": sim_node.name(),
                "type": sim_node.type().name(),
                "sim_type": sim_type.lower(),
                "position": [sim_node.position()[0], sim_node.position()[1]]
            }
        except Exception as e:
            print(f"Error in create_sim: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def run_simulation(self, 
                      node_path: str,
                      start_frame: int = 1,
                      end_frame: int = 10,
                      save_to_disk: bool = False) -> Dict[str, Any]:
        """Run a simulation for the specified node"""
        try:
            node = hou.node(node_path)
            if not node:
                raise ValueError(f"Node not found: {node_path}")
            
            # Check node type
            node_type = node.type().name().lower()
            if not any(sim_type in node_type for sim_type in ["dop", "pop", "crowd", "sim"]):
                raise ValueError(f"Node is not a simulation network: {node_path}")
            
            # Set up temporary directory for caches if saving to disk
            cache_path = None
            if save_to_disk:
                temp_dir = hou.expandString("$TEMP")
                cache_path = f"{temp_dir}/{node.name()}_cache"
                
                # Try to set cache parameter if it exists
                cache_parm = node.parm("dopoutput") or node.parm("cacheoutput")
                if cache_parm:
                    cache_parm.set(cache_path)
            
            # Store original frame range
            original_start = hou.playbar.frameRange()[0]
            original_end = hou.playbar.frameRange()[1]
            
            # Set simulation range
            hou.playbar.setFrameRange(start_frame, end_frame)
            
            # Run the simulation
            if node_type == "dopnet":
                node.parm("execute").pressButton()
            elif node_type == "popnet":
                node.parm("execute").pressButton()
            else:
                # Generic approach - try to cook the node for each frame
                for frame in range(start_frame, end_frame + 1):
                    hou.setFrame(frame)
                    node.cook(force=True)
            
            # Restore original frame range
            hou.playbar.setFrameRange(original_start, original_end)
            
            return {
                "success": True,
                "node": node_path,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "frames_simulated": end_frame - start_frame + 1,
                "cache_path": cache_path
            }
        except Exception as e:
            print(f"Error in run_simulation: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def export_fbx(self, 
                  node_path: str,
                  file_path: Optional[str] = None,
                  animation: bool = False) -> Dict[str, Any]:
        """Export a node to FBX format"""
        try:
            node = hou.node(node_path)
            if not node:
                raise ValueError(f"Node not found: {node_path}")
            
            # Generate file path if not provided
            if not file_path:
                temp_dir = hou.expandString("$TEMP")
                file_path = f"{temp_dir}/{node.name()}.fbx"
            
            # Ensure the path has an fbx extension
            if not file_path.endswith(".fbx"):
                file_path += ".fbx"
            
            # Export the node
            if animation:
                # Export with animation in frame range
                frame_range = hou.playbar.frameRange()
                hou.hipFile.exportFBX(
                    file_path,
                    [node],
                    start_frame=frame_range[0],
                    end_frame=frame_range[1],
                    use_obj_transform=True
                )
            else:
                # Export static model
                hou.hipFile.exportFBX(
                    file_path,
                    [node],
                    use_obj_transform=True
                )
            
            return {
                "success": True,
                "node": node_path,
                "file_path": file_path,
                "animation": animation
            }
        except Exception as e:
            print(f"Error in export_fbx: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def export_abc(self, 
                  node_path: str,
                  file_path: Optional[str] = None,
                  animation: bool = False) -> Dict[str, Any]:
        """Export a node to Alembic format"""
        try:
            node = hou.node(node_path)
            if not node:
                raise ValueError(f"Node not found: {node_path}")
            
            # Generate file path if not provided
            if not file_path:
                temp_dir = hou.expandString("$TEMP")
                file_path = f"{temp_dir}/{node.name()}.abc"
            
            # Ensure the path has an abc extension
            if not file_path.endswith(".abc"):
                file_path += ".abc"
            
            # Export the node - we need to use ROP Alembic Output
            rop = hou.node("/out") or hou.node("/").createNode("out")
            alembic_rop = rop.createNode("alembic")
            
            # Configure the ROP
            alembic_rop.parm("filename").set(file_path)
            alembic_rop.parm("root").set(node_path)
            
            if animation:
                # Export with animation
                frame_range = hou.playbar.frameRange()
                alembic_rop.parm("trange").set(1)  # Set to render frame range
                alembic_rop.parm("f1").set(frame_range[0])
                alembic_rop.parm("f2").set(frame_range[1])
            else:
                # Export single frame
                alembic_rop.parm("trange").set(0)  # Set to render current frame
            
            # Execute the ROP
            alembic_rop.parm("execute").pressButton()
            
            # Clean up - delete the temporary ROP
            alembic_rop.destroy()
            
            return {
                "success": True,
                "node": node_path,
                "file_path": file_path,
                "animation": animation
            }
        except Exception as e:
            print(f"Error in export_abc: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def export_usd(self, 
                  node_path: str,
                  file_path: Optional[str] = None,
                  animation: bool = False) -> Dict[str, Any]:
        """Export a node to USD format"""
        try:
            node = hou.node(node_path)
            if not node:
                raise ValueError(f"Node not found: {node_path}")
            
            # Generate file path if not provided
            if not file_path:
                temp_dir = hou.expandString("$TEMP")
                file_path = f"{temp_dir}/{node.name()}.usd"
            
            # Ensure the path has a usd extension
            if not file_path.endswith((".usd", ".usda", ".usdc")):
                file_path += ".usd"
            
            # Export the node - we need to use ROP USD Output
            rop = hou.node("/out") or hou.node("/").createNode("out")
            usd_rop = rop.createNode("usd")
            
            # Configure the ROP
            usd_rop.parm("lopoutput").set(file_path)
            usd_rop.parm("target").set(node_path)
            
            if animation:
                # Export with animation
                frame_range = hou.playbar.frameRange()
                usd_rop.parm("trange").set(1)  # Set to render frame range
                usd_rop.parm("f1").set(frame_range[0])
                usd_rop.parm("f2").set(frame_range[1])
            else:
                # Export single frame
                usd_rop.parm("trange").set(0)  # Set to render current frame
            
            # Execute the ROP
            usd_rop.parm("execute").pressButton()
            
            # Clean up - delete the temporary ROP
            usd_rop.destroy()
            
            return {
                "success": True,
                "node": node_path,
                "file_path": file_path,
                "animation": animation
            }
        except Exception as e:
            print(f"Error in export_usd: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def render_scene(self, 
                    output_path: Optional[str] = None,
                    renderer: str = "mantra",
                    resolution: Optional[List[int]] = None,
                    camera_path: Optional[str] = None) -> Dict[str, Any]:
        """Render the current scene using the specified renderer"""
        try:
            # Generate output path if not provided
            if not output_path:
                temp_dir = hou.expandString("$TEMP")
                output_path = f"{temp_dir}/houdinimcp_render.exr"
            
            # Ensure path has an extension
            if not any(output_path.endswith(ext) for ext in [".exr", ".jpg", ".png", ".tif", ".tiff"]):
                output_path += ".exr"
            
            # Create or find the ROP
            out_context = hou.node("/out")
            if not out_context:
                out_context = hou.node("/").createNode("out")
            
            # Create the appropriate ROP based on renderer
            renderer_map = {
                "mantra": "ifd",
                "karma": "karma",
                "arnold": "arnold",
                "redshift": "redshift_rop",
                "renderman": "renderman_rop"
            }
            
            rop_type = renderer_map.get(renderer.lower(), "ifd")
            
            # Try to find an existing ROP of the right type
            existing_rop = None
            for node in out_context.children():
                if node.type().name() == rop_type:
                    existing_rop = node
                    break
            
            if existing_rop:
                rop = existing_rop
            else:
                # Create a new ROP
                rop = out_context.createNode(rop_type)
            
            # Configure the ROP
            # Set output path
            if rop_type == "ifd":
                rop.parm("vm_picture").set(output_path)
            elif rop_type in ["karma", "arnold", "redshift_rop", "renderman_rop"]:
                rop.parm("output").set(output_path)
            
            # Set camera if provided
            if camera_path:
                camera = hou.node(camera_path)
                if camera:
                    rop.parm("camera").set(camera_path)
            
            # Set resolution if provided
            if resolution and len(resolution) == 2:
                rop.parm("res_override").set(1)  # Enable resolution override
                rop.parm("res_fraction").set("specific")
                rop.parm("res_overridex").set(resolution[0])
                rop.parm("res_overridey").set(resolution[1])
            
            # Set to render only one frame
            rop.parm("trange").set(0)  # Set to render current frame
            
            # Execute the ROP
            rop.parm("execute").pressButton()
            
            return {
                "success": True,
                "file_path": output_path,
                "renderer": renderer,
                "resolution": resolution or [rop.evalParm("res_overridex"), rop.evalParm("res_overridey")]
            }
        except Exception as e:
            print(f"Error in render_scene: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}

# Initialize the plugin
def init_houdinimcp():
    """Initialize the HoudiniMCP plugin"""
    try:
        # Check if the server is already running
        if hasattr(hou.session, "houdinimcp_server") and hou.session.houdinimcp_server:
            print("HoudiniMCP server is already running")
            return hou.session.houdinimcp_server
        
        # Create the server
        server = HoudiniMCPServer()
        if server.start():
            # Store in hou.session to keep it alive
            hou.session.houdinimcp_server = server
            return server
        else:
            print("Failed to start HoudiniMCP server")
            return None
    except Exception as e:
        print(f"Error initializing HoudiniMCP: {str(e)}")
        traceback.print_exc()
        return None

def stop_houdinimcp():
    """Stop the HoudiniMCP server"""
    try:
        if hasattr(hou.session, "houdinimcp_server") and hou.session.houdinimcp_server:
            hou.session.houdinimcp_server.stop()
            del hou.session.houdinimcp_server
            print("HoudiniMCP server stopped")
        else:
            print("HoudiniMCP server is not running")
    except Exception as e:
        print(f"Error stopping HoudiniMCP: {str(e)}")
        traceback.print_exc()

# Export functions
__all__ = ["init_houdinimcp", "stop_houdinimcp", "HoudiniMCPServer"]
