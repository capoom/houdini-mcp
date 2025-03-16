# HoudiniMCP Developer Guide

This guide is intended for developers who want to extend or modify the HoudiniMCP functionality.

## Architecture Overview

HoudiniMCP consists of two main components that work together:

1. **Houdini Addon** (`addon.py`): A Python module that runs within Houdini and sets up a socket server to receive commands.
2. **MCP Server** (`server.py`): A Python module that implements the Model Context Protocol (MCP) specification and forwards commands to Houdini.

Here's how the components interact:

```
Claude AI <--> MCP Server <--> Socket Connection <--> Houdini Addon <--> Houdini
```

## Adding New Tools

To add a new tool to HoudiniMCP, you need to modify both the addon and the server components.

### Step 1: Add a new command handler in addon.py

1. Locate the `execute_command` method in the `HoudiniMCPServer` class.
2. Add your new command to the `handlers` dictionary.
3. Implement a new method in the class to handle your command.

Example:

```python
# In the handlers dictionary
handlers = {
    # Existing handlers...
    "my_new_command": self.my_new_command,
}

# Add a new method to handle the command
def my_new_command(self, param1, param2=None):
    """Documentation for what this command does"""
    try:
        # Implement your command logic here
        result = {
            "success": True,
            "param1": param1,
            "custom_data": "Some processed data"
        }
        return result
    except Exception as e:
        print(f"Error in my_new_command: {str(e)}")
        traceback.print_exc()
        return {"error": str(e)}
```

### Step 2: Add a new tool in server.py

1. Add a new tool function with the `@mcp.tool()` decorator.
2. Implement the tool to forward the command to Houdini.

Example:

```python
@mcp.tool()
def my_new_tool(
    ctx: Context,
    param1: str,
    param2: Optional[str] = None
) -> str:
    """
    Description of what this tool does.
    
    Parameters:
    - param1: Description of first parameter
    - param2: Description of second parameter (optional)
    
    Returns:
    Information about the operation result.
    """
    try:
        houdini = get_houdini_connection()
        
        result = houdini.send_command("my_new_command", {
            "param1": param1,
            "param2": param2
        })
        
        if "error" in result:
            return f"Error executing command: {result['error']}"
        
        # Return a user-friendly message
        return f"Successfully executed command with param1={param1}"
    except Exception as e:
        logger.error(f"Error in my_new_tool: {str(e)}")
        return f"Error: {str(e)}"
```

## Developing Custom Houdini Integration

### Working with Houdini's Python API

HoudiniMCP uses the Houdini Object Model (HOM) API to interact with Houdini. Key modules include:

- `hou`: The main module for Houdini operations
- `hou.node()`: For accessing nodes in the scene
- `hou.parm()`: For accessing parameters
- `hou.geometry()`: For working with geometry

Refer to the [SideFX Houdini Python API documentation](https://www.sidefx.com/docs/houdini/hom/index.html) for complete details.

### Handling Complex Data Types

When passing data between Claude, the MCP server, and Houdini, keep these tips in mind:

1. All data must be JSON-serializable.
2. For complex Houdini types (like matrices, points, etc.), convert them to lists or dictionaries.
3. Handle large data volumes carefully to avoid timeout issues.

Example for converting a Houdini transformation matrix:

```python
def matrix_to_json(matrix):
    """Convert a hou.Matrix4 to a JSON-serializable format"""
    return [list(row) for row in matrix.asTupleOfTuples()]

def json_to_matrix(data):
    """Convert a JSON matrix representation back to hou.Matrix4"""
    return hou.Matrix4(data)
```

## Error Handling Best Practices

1. Use try/except blocks around all Houdini operations.
2. Log detailed error information on the server side.
3. Return user-friendly error messages to the client.
4. Include context about what was being attempted.

Example:

```python
try:
    # Risky operation
    result = some_houdini_operation()
    return {"success": True, "data": result}
except hou.OperationFailed as e:
    logger.error(f"Houdini operation failed: {str(e)}")
    return {"error": f"Couldn't complete the operation: {str(e)}"}
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    traceback.print_exc()
    return {"error": "An unexpected error occurred"}
```

## Protocol Extensions

The standard MCP protocol can be extended for Houdini-specific functionality:

1. Add custom attributes in the protocol's context.
2. Support file uploads/downloads for transferring assets.
3. Implement custom authentication if needed.

## Testing

1. Create a test suite that verifies each command works as expected.
2. Test with increasingly complex Houdini scenes.
3. Test error conditions and edge cases.
4. Consider using mock objects to test without a running Houdini instance.

Example test script:

```python
import unittest
from unittest.mock import MagicMock, patch
from houdini_mcp.server import get_houdini_connection, create_geometry

class TestHoudiniMCP(unittest.TestCase):
    @patch('houdini_mcp.server.get_houdini_connection')
    def test_create_geometry(self, mock_get_connection):
        # Setup mock
        mock_connection = MagicMock()
        mock_connection.send_command.return_value = {
            "path": "/obj/geo1",
            "name": "geo1",
            "type": "box"
        }
        mock_get_connection.return_value = mock_connection
        
        # Call function
        result = create_geometry(None, "box", "/obj", "geo1")
        
        # Assert command was sent correctly
        mock_connection.send_command.assert_called_with(
            "create_geometry", 
            {"geo_type": "box", "parent_path": "/obj", "name": "geo1"}
        )
        
        # Assert result is formatted correctly
        self.assertIn("Created box geometry at /obj/geo1", result)

if __name__ == '__main__':
    unittest.main()
```

## Contributing

When contributing to this project:

1. Fork the repository and create a feature branch.
2. Add tests for new functionality.
3. Ensure all tests pass.
4. Submit a pull request with a clear description of the changes.
5. Update documentation to reflect your changes.

For major changes, please open an issue first to discuss what you would like to change.

## Performance Considerations

1. Minimize the number of round-trips between the MCP server and Houdini.
2. Batch operations when possible.
3. Be aware that some Houdini operations can be slow (e.g., complex simulations).
4. Consider implementing progress reporting for long-running operations.

## Security Considerations

1. Avoid exposing the Houdini server to untrusted networks.
2. Be cautious with the `execute_houdini_code` command, as it can run arbitrary code.
3. Validate all inputs before passing them to Houdini.
4. Consider adding authentication to the socket connection if needed.
