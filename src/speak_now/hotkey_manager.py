import keyboard

class HotkeyManager:
    def __init__(self, config, text_cache):
        self.config = config
        self.text_cache = text_cache
        self.hotkeys_registered = False
        self.recorder = None

    def _on_paste_raw(self):
        # Directly call text_cache’s raw paste; do not manually release ctrl/alt
        self.text_cache.paste_and_clear()

    def _on_paste_formatted(self):
        # Directly call text_cache’s format & paste
        self.text_cache.format_and_paste()

    def register_hotkeys(self):
        """Register keyboard hotkeys and return success status."""
        try:
            # Fire on key release to avoid the user needing to hold keys for too long
            keyboard.add_hotkey(
                self.config["hotkeys"]["paste_raw"], 
                callback=self._on_paste_raw, 
                trigger_on_release=True
            )

            keyboard.add_hotkey(
                self.config["hotkeys"]["paste_formatted"],
                callback=self._on_paste_formatted,
                trigger_on_release=True
            )

            keyboard.add_hotkey(
                self.config["hotkeys"]["toggle_recording"],
                self._toggle_recording,
                trigger_on_release=True
            )

            self.hotkeys_registered = True
            print("[Hotkeys] Successfully registered hotkeys")
            return True
        except Exception as e:
            print(f"[Hotkeys] Failed to register hotkeys: {e}")
            return False

    def _toggle_recording(self):
        # Toggle is built right into the notification
        if hasattr(self.text_cache.notification, "_toggle_recording"):
            self.text_cache.notification._toggle_recording()

    def set_recorder(self, recorder):
        self.recorder = recorder

    def is_registered(self):
        return self.hotkeys_registered

    def unregister(self):
        try:
            keyboard.unhook_all()
            self.hotkeys_registered = False
            print("[Hotkeys] Unregistered all hotkeys")
        except Exception as e:
            print(f"[Hotkeys] Error unregistering hotkeys: {e}")
