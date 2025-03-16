# HoudiniMCP - Houdini Model Context Protocol Integration

HoudiniMCP connects Houdini to Claude AI through the Model Context Protocol (MCP), allowing Claude to directly interact with and control Houdini. This integration enables prompt-assisted 3D modeling, scene creation, simulation setup, and rendering.

## Features

- **Two-way communication**: Connect Claude AI to Houdini through a socket-based server
- **Node manipulation**: Create, modify, and delete nodes in Houdini networks
- **Geometry creation**: Generate various primitive types with customizable parameters
- **Material control**: Apply and modify materials 
- **Scene inspection**: Get detailed information about the current Houdini scene
- **Simulation setup**: Create and run physics simulations (fluids, particles, etc.)
- **Rendering control**: Configure and execute rendering operations
- **Code execution**: Run arbitrary Python code in Houdini from Claude

## Components

The system consists of two main components:

1. **Houdini Addon (`addon.py`)**: A Houdini Python extension that creates a socket server within Houdini to receive and execute commands
2. **MCP Server (`src/houdini_mcp/server.py`)**: A Python server that implements the Model Context Protocol and connects to the Houdini addon

## Installation

### Prerequisites

- Houdini 19.0 or newer
- Python 3.10 or newer
- uv package manager: 

**If you're on Mac, please install uv as**
```bash
brew install uv
```
**On Windows**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex" 
```
and then
```bash
set Path=C:\Users\username\.local\bin;%Path%
```

Otherwise installation instructions are on their website: [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

**⚠️ Do not proceed before installing UV**

### Claude for Desktop Integration

Go to Claude > Settings > Developer > Edit Config > claude_desktop_config.json to include the following:

```json
{
    "mcpServers": {
        "houdini": {
            "command": "uvx",
            "args": [
                "houdini-mcp"
            ]
        }
    }
}
```

### Cursor integration

Run houdini-mcp without installing it permanently through uvx. Go to Cursor Settings > MCP and paste this as a command.

```bash
uvx houdini-mcp
```

**⚠️ Only run one instance of the MCP server (either on Cursor or Claude Desktop), not both**

### Installing the Houdini Addon

1. Download the `addon.py` file from this repo
2. Copy it to your Houdini Python scripts directory:
   - Windows: `C:\Users\username\Documents\houdini19.x\scripts\`
   - Mac: `/Users/username/Library/Preferences/houdini/19.x/scripts/`
   - Linux: `~/houdini19.x/scripts/`
3. Start Houdini and run the following Python code in a Python panel:
   ```python
   import addon
   server = addon.init_houdinimcp()
   ```

## Usage

### Starting the Connection

1. In Houdini, run the Python code to initialize the server:
   ```python
   import addon
   server = addon.init_houdinimcp()
   ```
2. Verify that you see a message: "HoudiniMCP server started on localhost:9877"

3. Make sure the MCP server is running in your terminal

### Using with Claude

Once the config file has been set on Claude, and the addon is running on Houdini, you will see a hammer icon with tools for the Houdini MCP.

#### Tools

- `get_scene_info` - Gets scene information
- `get_node_info` - Gets detailed information for a specific node in the scene
- `create_node` - Create a new node with detailed parameters
- `create_geometry` - Create basic primitive geometry with customizable parameters
- `modify_node` - Modify an existing node's properties
- `delete_node` - Remove a node from the scene
- `set_parameter` - Set a single parameter of a node
- `connect_nodes` - Connect two nodes together
- `set_material` - Apply or create materials for objects
- `create_camera` - Create a camera with positioning options
- `create_light` - Create a light with customizable type and parameters
- `create_simulation` - Set up a simulation network for physics
- `run_simulation` - Execute a simulation for a specified frame range
- `render_scene` - Render the current scene with configurable options
- `export_fbx` - Export a node to FBX format
- `execute_houdini_code` - Run any Python code in Houdini

### Example Commands

Here are some examples of what you can ask Claude to do:

- "Create a procedural landscape with mountains and a river"
- "Set up a fluid simulation with a box emitter"
- "Create a sphere and apply a red material to it"
- "Modify the camera to have a wide-angle lens"
- "Get information about the current scene network"
- "Export the selected object as an FBX file"
- "Create a particle system with gravity and collision"

## Troubleshooting

- **Connection issues**: Make sure the Houdini addon server is running, and the MCP server is configured on Claude.
- **Timeout errors**: Try simplifying your requests or breaking them into smaller steps.
- **Have you tried turning it off and on again?**: If you're still having connection errors, try restarting both Claude and the Houdini server.

## Technical Details

### Communication Protocol

The system uses a simple JSON-based protocol over TCP sockets:

- **Commands** are sent as JSON objects with a `type` and optional `params`
- **Responses** are JSON objects with a `status` and `result` or `message`

## Limitations & Security Considerations

- The `execute_houdini_code` tool allows running arbitrary Python code in Houdini, which can be powerful but potentially dangerous. Use with caution in production environments. ALWAYS save your work before using it.
- Complex operations might need to be broken down into smaller steps.
- Houdini's node-based system is powerful but complex - some operations may require multiple steps to achieve the desired result.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a third-party integration and not made by SideFX.
