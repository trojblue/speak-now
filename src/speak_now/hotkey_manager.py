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

    def _on_paste_raw(self):
        import keyboard
        # Force-release Alt in case it’s stuck
        keyboard.release('ctrl')
        self.text_cache.paste_and_clear()
        keyboard.release('ctrl')


    def _on_paste_formatted(self):
        import keyboard
        # Force-release Alt in case it’s stuck
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