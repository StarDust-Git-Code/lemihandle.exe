import requests
import base64
import json
from PIL import ImageGrab
import io

SERVER_URL = "http://localhost:8000"

def capture_screen_base64() -> str:
    """Takes a screenshot of the primary monitor and returns it as a base64 string."""
    print("[*] Taking screenshot...")
    screenshot = ImageGrab.grab()
    
    # Compress the image aggressively to save network latency
    screenshot.thumbnail((800, 600))
    
    img_byte_arr = io.BytesIO()
    # Save as JPEG with 50% quality for ultra-fast upload
    screenshot.save(img_byte_arr, format='JPEG', quality=50)
    img_bytes = img_byte_arr.getvalue()
    
    b64_encoded = base64.b64encode(img_bytes).decode('utf-8')
    print("[*] Screenshot captured and encoded.")
    return b64_encoded

def interactive_test():
    print("==================================================")
    print(" Lemihandle - Interactive Backend Test")
    print("==================================================")
    
    while True:
        command = input("\n[You] Enter command (or 'quit' to exit): ")
        if command.lower() in ('quit', 'exit', 'q'):
            break
            
        screen_b64 = capture_screen_base64()
        
        payload = {
            "trigger_type": "interactive_test",
            "screen_b64": screen_b64,
            "audio_transcript": command
        }
        
        print("\n[*] Sending payload to Lemihandle Brain...")
        try:
            r = requests.post(f"{SERVER_URL}/process_intent", json=payload)
            
            if r.status_code == 200:
                data = r.json()
                print("\n[LEMIHANDLE RESPONSE]")
                print(f"Status:      {data.get('status')}")
                print(f"UI Directive:{data.get('ui_directive')}")
                print(f"AI Output:   {data.get('ai_output')}")
                print(f"Tool Trigger:{data.get('function_triggered')}")
            else:
                print(f"\n[ERROR] Server returned {r.status_code}: {r.text}")
                
        except requests.exceptions.ConnectionError:
            print("\n[ERROR] Could not connect to the server. Is it running?")
            break
            
if __name__ == "__main__":
    interactive_test()
