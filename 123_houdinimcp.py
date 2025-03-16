import sys
import hou

# Add the path to your addon.py
sys.path.append(r"D:\Github\houdini-mcp")

try:
    # Import and initialize the addon
    import addon
    server = addon.init_houdinimcp()
    
    if server:
        print("HoudiniMCP server started successfully!")
    else:
        print("Failed to start HoudiniMCP server.")
except Exception as e:
    print(f"Error starting HoudiniMCP: {str(e)}")