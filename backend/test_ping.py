import requests
import base64
import json
from io import BytesIO
from PIL import Image

API_URL = "http://localhost:8000"

def create_dummy_image_b64() -> str:
    """Creates a tiny red image and returns it as base64."""
    img = Image.new('RGB', (10, 10), color='red')
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def test_health():
    print("--- Testing /health ---")
    try:
        r = requests.get(f"{API_URL}/health")
        print(f"Status Code: {r.status_code}")
        print(f"Response: {r.json()}\n")
    except Exception as e:
        print(f"Connection failed: {e}\nIs the server running?")
        return False
    return True

def test_process_intent():
    print("--- Testing /process_intent ---")
    
    payload = {
        "trigger_type": "hotkey",
        "screen_b64": create_dummy_image_b64(),
        "audio_transcript": "Describe what color you see in the screenshot. Then save your description to a file named 'color_test.txt'."
    }
    
    print("Sending POST request (this may take a few seconds)...")
    r = requests.post(f"{API_URL}/process_intent", json=payload)
    
    print(f"Status Code: {r.status_code}")
    try:
        # Pretty print JSON response
        data = r.json()
        print(json.dumps(data, indent=2))
        
        if data.get("status") == "success":
            print("\n[SUCCESS]: Received structured JSON response.")
            print(f"Function Triggered: {data.get('function_triggered')}")
        else:
            print("\n[FAILED]: Status is not success.")
            
    except Exception as e:
        print(f"[FAILED] to parse response: {r.text}")

if __name__ == "__main__":
    if test_health():
        test_process_intent()
