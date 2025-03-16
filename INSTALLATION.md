# HoudiniMCP Installation Guide

This guide provides step-by-step instructions for installing and configuring HoudiniMCP to enable Claude AI to interact with Houdini.

## Prerequisites

Before installing HoudiniMCP, make sure you have:

1. **Houdini** - Version 19.0 or newer
2. **Python** - Version 3.10 or newer
3. **Claude for Desktop** or **Cursor** - For accessing Claude AI with MCP support
4. **uv package manager** - For dependency management

## Step 1: Install the uv package manager

### On macOS:
```bash
brew install uv
```

### On Windows:
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Then add to your PATH:
```bash
set Path=C:\Users\username\.local\bin;%Path%
```

### On Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Step 2: Install HoudiniMCP package

You can install HoudiniMCP using one of these methods:

### Option A: Install from GitHub
```bash
pip install git+https://github.com/yourusername/houdini-mcp.git
```

### Option B: Install locally
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/houdini-mcp.git
   cd houdini-mcp
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

## Step 3: Configure the Houdini Addon

1. Copy the `addon.py` file to your Houdini Python scripts directory:

   - **Windows**: `C:\Users\username\Documents\houdini19.x\scripts\`
   - **macOS**: `/Users/username/Library/Preferences/houdini/19.x/scripts/`
   - **Linux**: `~/houdini19.x/scripts/`

2. Create a startup script to automatically load the addon when Houdini starts.
   
   Create a file named `123_houdinimcp.py` in the same scripts directory with the following content:
   
   ```python
   import hou
   
   def initializeHoudiniMCP():
       try:
           import addon
           server = addon.init_houdinimcp()
           if server:
               print("HoudiniMCP server started successfully")
       except Exception as e:
           print(f"Error starting HoudiniMCP: {str(e)}")
   
   # Add a slight delay to ensure Houdini is fully loaded
   hou.ui.addEventLoopCallback(lambda: initializeHoudiniMCP())
   ```

## Step 4: Configure Claude for Desktop

1. Open Claude for Desktop
2. Go to Settings > Developer > Edit Config
3. Edit the `claude_desktop_config.json` file to include:

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

4. Save the file and restart Claude for Desktop

## Step 5: Configure Cursor (Alternative to Claude for Desktop)

If you're using Cursor instead of Claude for Desktop:

1. Go to Cursor Settings > MCP
2. Add a new command:
   ```bash
   uvx houdini-mcp
   ```

## Step 6: Testing the Connection

1. Start Houdini
2. Verify that you see a message in the console: "HoudiniMCP server started on localhost:9877"
3. Open Claude for Desktop or Cursor
4. Ask Claude to interact with Houdini by trying a simple command:
   ```
   Use Houdini to create a sphere in the scene
   ```

If everything is set up correctly, Claude should be able to create a sphere in Houdini.

## Troubleshooting

### Connection Issues

- **Server not starting**: Check if the port 9877 is already in use by another application
- **Claude can't connect**: Make sure the MCP server is running and the configuration in Claude is correct
- **Timeout errors**: Try simpler commands first to verify basic connectivity

### Permission Issues

- **File access errors**: Ensure Houdini has permissions to write to temporary directories
- **Addon loading errors**: Check that the addon.py file is in the correct directory

### Python Version Conflicts

- **Module import errors**: Make sure the Python version used by HoudiniMCP matches the one used by Houdini
- **Dependency issues**: Try installing dependencies manually: `pip install mcp[cli]>=1.3.0`

For additional help, check the [README.md](README.md) file or submit an issue on GitHub.
