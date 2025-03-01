import time
import winsound
import requests

# ---------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------
def generate_gemini(prompt, api_key, model):
    """Generates content using Google's Generative Language API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    data = {
        "contents": [
            {"parts": [{"text": prompt}]},
        ],
    }
    response = requests.post(url, json=data, headers=headers, params=params)
    
    if response.status_code != 200:
        raise Exception(f"API request failed: {response.status_code} - {response.text}")
    
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError("Unexpected API response format") from e

def play_sound(sound_type):
    """Play different sounds based on the action."""
    try:
        if sound_type == "startup":
            winsound.Beep(600, 150)
            time.sleep(0.05)
            winsound.Beep(800, 150)
            time.sleep(0.05)
            winsound.Beep(1000, 150)
        elif sound_type == "text_added":
            winsound.Beep(1000, 100)
        elif sound_type == "processing":
            winsound.Beep(900, 60)
        elif sound_type == "paste_raw":
            winsound.Beep(800, 100)
            time.sleep(0.03)
            winsound.Beep(1200, 100)
        elif sound_type == "paste_formatted":
            winsound.Beep(900, 100)
            time.sleep(0.03)
            winsound.Beep(1300, 100)
        elif sound_type == "error":
            winsound.Beep(400, 200)
        elif sound_type == "toggle_recording":
            winsound.Beep(600, 100)
            time.sleep(0.03)
            winsound.Beep(1100, 100)
    except Exception as e:
        print(f"Sound error: {e}")