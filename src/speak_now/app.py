import time

from speak_now.config import load_config
from speak_now.utils import generate_gemini, play_sound, cleanup_audio
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
        self.recorder_active = True  # Track if recorder is currently active
        self.recorder_initialized = False  # Track if recorder has been initialized


    def start(self):
        """Start the application."""
        print("Enhanced Speech-to-Text with AI Formatting")
        print("==========================================")
        print(f"Paste raw text: {self.config['hotkeys']['paste_raw']}")
        print(f"Format & paste: {self.config['hotkeys']['paste_formatted']}")
        print(f"Toggle recording: {self.config['hotkeys']['toggle_recording']}")
        
        # Add new toggle window hotkey to the output
        if "toggle_window" in self.config["hotkeys"]:
            print(f"Toggle window: {self.config['hotkeys']['toggle_window']}")
        
        print("Use the GUI window to select formatting style and view history.")
        
        # Inform user if starting in hidden mode
        if self.config["ui"].get("start_hidden", False):
            print("Starting with GUI hidden. UI will not appear automatically.")
            print(f"Use {self.config['hotkeys'].get('toggle_window', 'toggle window hotkey')} to show/hide interface.")
        
        print("Press Ctrl+C in terminal to exit.\n")

        # Register hotkeys
        if not self.hotkey_manager.register_hotkeys():
            print("[ERROR] Failed to register hotkeys. Try restarting the application.")
            print(
                "If the problem persists, check if another application is using the same hotkeys."
            )
            return False

        try:
            # Import STT library here to handle import errors gracefully
            from RealtimeSTT import AudioToTextRecorder

            # Store the recorder class for later initialization
            self.RecorderClass = AudioToTextRecorder
            
            # Initialize the recorder only if needed (not starting in muted state)
            if self.text_cache.notification.is_recording_enabled():
                self._initialize_recorder()
            else:
                # If we're starting in a muted state, don't initialize the recorder yet
                print("[Main] Starting with recording disabled - microphone not initialized")
                self.recorder_active = False

            # Set app reference in notification for microphone control
            self.text_cache.notification.set_app_reference(self)

            # Set recorder reference in hotkey manager
            self.hotkey_manager.set_recorder(self)

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

    def _initialize_recorder(self):
        """Initialize the audio recorder if not already initialized."""
        if not self.recorder_initialized:
            self.recorder = self.RecorderClass(model=self.config["stt"]["model"])
            self.recorder.timeout = self.config["stt"]["timeout"]
            self.recorder_initialized = True
            print("[Main] Initialized microphone recorder")
        self.recorder_active = True

    def _shutdown_recorder(self):
        """Shut down the recorder to free the microphone."""
        if self.recorder_initialized and self.recorder:
            try:
                self.recorder.shutdown()
                self.recorder = None
                self.recorder_initialized = False
                print("[Main] Released microphone")
            except Exception as e:
                print(f"[Error] Failed to shut down recorder: {e}")
        self.recorder_active = False

    def toggle_microphone(self, recording_state):
        """Toggle microphone usage based on recording state."""
        if recording_state and not self.recorder_active:
            # If recording should be enabled but recorder is inactive, initialize it
            self._initialize_recorder()
            print("[Main] Microphone activated")
        elif not recording_state and self.recorder_active:
            # If recording should be disabled but recorder is active, shut it down
            self._shutdown_recorder()
            print("[Main] Microphone deactivated")

    def _run_main_loop(self):
        """Run the main application loop."""
        try:
            while True:
                # Only process audio if recording is enabled and recorder is active
                if self.text_cache.notification.is_recording_enabled() and self.recorder_active and self.recorder:
                    self.recorder.text(
                        lambda recognized_text: self.text_cache.add_text(
                            recognized_text
                        )
                    )
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n[Main] Exiting by user request...")

    def cleanup(self):
        """Clean up resources before exit."""
        # Shutdown the recorder
        if self.recorder and self.recorder_initialized:
            self._shutdown_recorder()

        # Unregister hotkeys
        self.hotkey_manager.unregister()

        # Clean up text cache and notification
        self.text_cache.cleanup()

        # Clean up audio resources
        cleanup_audio()