import keyboard

# ---------------------------------------------------------------------
# HOTKEY HANDLING
# ---------------------------------------------------------------------
class HotkeyManager:
    def __init__(self, config, text_cache):
        self.config = config
        self.text_cache = text_cache
        self.hotkeys_registered = False
        self.recorder = None
        self.app = None  # Reference to main app

    def _on_paste_raw(self):
        import keyboard
        # Force-release Alt in case it's stuck
        keyboard.release('ctrl')
        self.text_cache.paste_and_clear()
        keyboard.release('ctrl')

    def _on_paste_formatted(self):
        import keyboard
        # Force-release Alt in case it's stuck
        keyboard.release('alt')
        self.text_cache.format_and_paste()

    def register_hotkeys(self):
        """Register keyboard hotkeys and return success status."""
        try:
            keyboard.add_hotkey(
                self.config["hotkeys"]["paste_raw"], self.text_cache.paste_and_clear
            )

            keyboard.add_hotkey(
                self.config["hotkeys"]["paste_formatted"],
                lambda: self._on_paste_formatted(),
            )

            keyboard.add_hotkey(
                self.config["hotkeys"]["toggle_recording"], self._toggle_recording
            )
            
            # Add new hotkey for toggling window visibility
            if "toggle_window" in self.config["hotkeys"]:
                keyboard.add_hotkey(
                    self.config["hotkeys"]["toggle_window"], self._toggle_window_visibility
                )

            self.hotkeys_registered = True
            print(f"[Hotkeys] Successfully registered hotkeys")
            return True
        except Exception as e:
            print(f"[Hotkeys] Failed to register hotkeys: {e}")
            return False

    def _toggle_recording(self):
        """Toggle recording via hotkey."""
        if hasattr(self.text_cache.notification, "_toggle_recording"):
            self.text_cache.notification._toggle_recording()
    
    def _toggle_window_visibility(self):
        """Toggle window visibility via hotkey."""
        if hasattr(self.text_cache.notification, "toggle_window_visibility"):
            # We'll keep using the existing toggle_recording sound for window visibility
            # since it's a different action and doesn't need the mute/unmute distinction
            self.text_cache.notification.toggle_window_visibility()

    def set_recorder(self, app_or_recorder):
        """Set recorder or app reference for control operations."""
        # The app now passes itself as a reference
        if hasattr(app_or_recorder, 'recorder'):
            self.app = app_or_recorder
            self.recorder = app_or_recorder.recorder
        else:
            # For backward compatibility
            self.recorder = app_or_recorder

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