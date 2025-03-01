from RealtimeSTT import AudioToTextRecorder
import pyautogui

def process_text(text):
    pyautogui.typewrite(text + " ")

if __name__ == '__main__':
    print("Wait until it says 'speak now'")
    # recorder = AudioToTextRecorder(model="medium.en")
    recorder = AudioToTextRecorder(model="large-v2")

    while True:
        recorder.text(process_text)