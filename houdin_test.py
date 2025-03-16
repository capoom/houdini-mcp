"""Simple test script to verify Houdini connection"""
import socket
import json

def test_houdini_connection():
    print("Testing connection to Houdini...")
    
    try:
        # Create socket connection
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('localhost', 9877))
        print("Connected to Houdini successfully!")
        
        # Send a simple command to get scene info
        command = {
            "type": "get_scene_info",
            "params": {}
        }
        
        print("Sending command to get scene info...")
        client.sendall(json.dumps(command).encode('utf-8'))
        
        # Receive response
        print("Waiting for response...")
        response_data = client.recv(8192)
        response = json.loads(response_data.decode('utf-8'))
        
        print("\nResponse from Houdini:")
        print(json.dumps(response, indent=2))
        
        print("\nConnection test completed successfully!")
        
        # Try creating a sphere
        print("\nTrying to create a sphere...")
        sphere_command = {
            "type": "create_geometry",
            "params": {
                "geo_type": "sphere",
                "parent_path": "/obj",
                "name": "test_sphere"
            }
        }
        
        client.sendall(json.dumps(sphere_command).encode('utf-8'))
        
        # Receive response
        sphere_response_data = client.recv(8192)
        sphere_response = json.loads(sphere_response_data.decode('utf-8'))
        
        print("\nSphere creation response:")
        print(json.dumps(sphere_response, indent=2))
        
        client.close()
        return True
        
    except Exception as e:
        print(f"Error testing connection: {str(e)}")
        return False

if __name__ == "__main__":
    test_houdini_connection()
