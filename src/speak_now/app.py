import time

from speak_now.config import load_config
from speak_now.utils import generate_gemini, play_sound
from speak_now.gui_notification import EnhancedNotification
from speak_now.text_cache import TextCache
from speak_now.hotkey_manager import HotkeyManager

# ---------------------------------------------------------------------
# MAIN APPLICATION CLASS
# ---------------------------------------------------------------------
class SpeechTranscriptionApp:
    def __init__(self, config_file="stt_config.toml"):
        # Load configuration
        self.config = load_config(config_file)
        
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