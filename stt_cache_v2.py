import os
import sys
import time
import json
import queue
import threading
import requests
import pyautogui
import pyperclip
import keyboard
import winsound
import toml
from datetime import datetime
from tkinter import Tk, Toplevel, Label, Frame, Button, OptionMenu, StringVar, Scrollbar, Listbox, BooleanVar, Checkbutton

# ---------------------------------------------------------------------
# CONFIGURATION MANAGEMENT
# ---------------------------------------------------------------------
from speak_now.config import load_config
from speak_now.utils import generate_gemini, play_sound
from speak_now.gui_notification import EnhancedNotification
from speak_now.text_cache import TextCache
CONFIG_FILE = "stt_config.toml"




# ---------------------------------------------------------------------
# HOTKEY HANDLING
# ---------------------------------------------------------------------
class HotkeyManager:
    def __init__(self, config, text_cache):
        self.config = config
        self.text_cache = text_cache
        self.hotkeys_registered = False
        self.recorder = None

    def register_hotkeys(self):
        """Register keyboard hotkeys and return success status."""
        try:
            keyboard.add_hotkey(
                self.config["hotkeys"]["paste_raw"], 
                self.text_cache.paste_and_clear
            )
            
            keyboard.add_hotkey(
                self.config["hotkeys"]["paste_formatted"], 
                lambda: self.text_cache.format_and_paste()
            )
            
            keyboard.add_hotkey(
                self.config["hotkeys"]["toggle_recording"],
                self._toggle_recording
            )
            
            self.hotkeys_registered = True
            print(f"[Hotkeys] Successfully registered hotkeys")
            return True
        except Exception as e:
            print(f"[Hotkeys] Failed to register hotkeys: {e}")
            return False
            
    def _toggle_recording(self):
        """Toggle recording via hotkey."""
        if hasattr(self.text_cache.notification, '_toggle_recording'):
            self.text_cache.notification._toggle_recording()
            
    def set_recorder(self, recorder):
        """Set recorder reference for control operations."""
        self.recorder = recorder
            
    def is_registered(self):
        """Check if hotkeys were successfully registered."""
        return self.hotkeys_registered
        
    def unregister(self):
        """Unregister all hotkeys."""
        try:
            keyboard.unhook_all()
            self.hotkeys_registered = False
            print("[Hotkeys] Unregistered all hotkeys")
        except Exception as e:
            print(f"[Hotkeys] Error unregistering hotkeys: {e}")

# ---------------------------------------------------------------------
# MAIN APPLICATION CLASS
# ---------------------------------------------------------------------
class SpeechTranscriptionApp:
    def __init__(self):
        # Load configuration
        self.config = load_config(CONFIG_FILE)
        
        # Initialize components
        self.text_cache = TextCache(self.config)
        self.hotkey_manager = HotkeyManager(self.config, self.text_cache)
        self.recorder = None
        
    def start(self):
        """Start the application."""
        print("Enhanced Speech-to-Text with AI Formatting")
        print("==========================================")
        print(f"Paste raw text: {self.config['hotkeys']['paste_raw']}")
        print(f"Format & paste: {self.config['hotkeys']['paste_formatted']}")
        print(f"Toggle recording: {self.config['hotkeys']['toggle_recording']}")
        print("Use the GUI window to select formatting style and view history.")
        print("Press Ctrl+C in terminal to exit.\n")

        # Register hotkeys
        if not self.hotkey_manager.register_hotkeys():
            print("[ERROR] Failed to register hotkeys. Try restarting the application.")
            print("If the problem persists, check if another application is using the same hotkeys.")
            return False
        
        try:
            # Import STT library here to handle import errors gracefully
            from RealtimeSTT import AudioToTextRecorder
            
            # Initialize the audio recorder
            self.recorder = AudioToTextRecorder(
                model=self.config["stt"]["model"]
            )
            self.recorder.timeout = self.config["stt"]["timeout"]
            
            # Set recorder reference in hotkey manager
            self.hotkey_manager.set_recorder(self.recorder)
            
            # Play startup sound
            play_sound("startup")
            
            # Start the main loop
            self._run_main_loop()
            
        except ImportError as e:
            print(f"[ERROR] Could not import RealtimeSTT: {e}")
            print("Please make sure the library is installed (pip install RealtimeSTT)")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to start application: {e}")
            return False
        finally:
            self.cleanup()
            
        return True
            
    def _run_main_loop(self):
        """Run the main application loop."""
        try:
            while True:
                # Only process audio if recording is enabled
                if self.text_cache.notification.is_recording_enabled():
                    self.recorder.text(lambda recognized_text: self.text_cache.add_text(recognized_text))
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n[Main] Exiting by user request...")

    def cleanup(self):
        """Clean up resources before exit."""
        # Shutdown the recorder
        if self.recorder:
            try:
                self.recorder.shutdown()
            except Exception as e:
                print(f"[Error] Failed to shut down recorder: {e}")
        
        # Unregister hotkeys
        self.hotkey_manager.unregister()
        
        # Clean up text cache and notification
        self.text_cache.cleanup()

# ---------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------
def main():
    app = SpeechTranscriptionApp()
    app.start()

if __name__ == '__main__':
    main()