import pyperclip
import pyautogui
import threading
import time
import os
from .utils import generate_gemini

from .gui_notification import EnhancedNotification
from .utils import play_sound


# ---------------------------------------------------------------------
# TEXT CACHE (CORE LOGIC)
# ---------------------------------------------------------------------
class TextCache:
    def __init__(self, config):
        self.cache = ""  # Current text in memory
        self.previous_raw = ""  # Last raw text that was pasted
        self.last_unformatted_text = ""
        self.last_formatted_text = ""
        self.last_format_used = None
        self.config = config

        self.is_pasting = False
        self.is_formatting = False
        self.lock = threading.Lock()

        self.notification = EnhancedNotification(
            format_callback=self.format_and_paste, config=config
        )
        self.notification.set_raw_paste_callback(self.paste_and_clear)

        self.api_key = self.config["api"]["gemini_api_key"] or os.environ.get(
            "GEMINI_API_KEY", ""
        )

    def add_text(self, text):
        """Add recognized speech to the text cache."""
        # Skip if recording is disabled
        if not self.notification.is_recording_enabled():
            return

        with self.lock:
            self.cache += text + " "
            print(f"[TextCache] Added to cache: '{text}'")
            play_sound("text_added")
            self.notification.show_content(self.cache)
            self._update_status()

    def paste_and_clear(self):
        """
        Paste the current cache, then clear.
        If cache is empty, re-paste previous_raw.
        """
        print(
            f"[TextCache] Hotkey triggered: {self.config['hotkeys']['paste_raw']} (raw paste)"
        )
        with self.lock:
            text_to_paste = (
                self.cache.strip() if self.cache.strip() else self.previous_raw
            )

            if not text_to_paste:
                print("[TextCache] Nothing to paste (empty cache + no previous raw).")
                play_sound("error")
                self.notification.update_status("Cache is empty, nothing to paste")
                return

            self.is_pasting = True
            try:
                self._update_status()

                # If new text is in the cache, update previous_raw
                if self.cache.strip():
                    self.previous_raw = text_to_paste
                    self.notification.message_queue.put(("add_history", text_to_paste))

                self.cache = ""  # Clear it now that we have "finished" that chunk.

                # Actually paste
                self._perform_paste_operation(text_to_paste)

                play_sound("paste_raw")
                self.notification.update_status("Text pasted! Cache cleared.")
                print(f"[TextCache] Pasted raw text: '{text_to_paste}'")

            finally:
                self.is_pasting = False
                self._update_status()

    def format_and_paste(self, text=None, format_type=None):
        """
        Format the text using Gemini (if needed) and then paste.
        """
        print(
            f"[TextCache] Hotkey triggered: {self.config['hotkeys']['paste_formatted']} (format & paste)"
        )
        with self.lock:
            # If no text provided, we use what's in the cache:
            text_to_format = text.strip() if text else self.cache.strip()

            # If still nothing, fallback to previous_raw
            if not text_to_format:
                text_to_format = self.previous_raw

            if not text_to_format:
                print("[TextCache] Nothing to format (empty cache + no previous raw).")
                play_sound("error")
                self.notification.update_status("Nothing to format - cache is empty")
                return

            # If no format_type, get from GUI
            if not format_type:
                format_type = self.notification.get_current_format()

            # If user says "None", just raw paste
            if format_type == "None":
                # If we have new text in cache, do a normal paste_and_clear
                if text == self.cache:
                    self.paste_and_clear()
                else:
                    self._paste_direct(text_to_format, is_formatted=False)
                return

            # Process formatting request
            self._handle_formatting(text, text_to_format, format_type)

    def _handle_formatting(self, original_text, text_to_format, format_type):
        """Handle the formatting part of format_and_paste."""
        self.is_formatting = True
        try:
            play_sound("processing")
            self._update_status()
            self.notification.update_status(f"Formatting with {format_type}...")

            # If we are formatting new text from the cache, set previous_raw
            if original_text == self.cache and self.cache.strip():
                self.previous_raw = text_to_format
                self.notification.message_queue.put(("add_history", text_to_format))

            # Check if we can reuse a previous format
            same_unformatted = text_to_format == self.last_unformatted_text
            same_format = format_type == self.last_format_used

            if same_unformatted and same_format and self.last_formatted_text:
                print(
                    "[TextCache] Reusing previously formatted text (no new LLM call)."
                )
                formatted_text = self.last_formatted_text
                self.notification.show_format_result(formatted_text)
                self._paste_direct(formatted_text, is_formatted=True)
            else:
                self._format_with_api(text_to_format, format_type, original_text)

        except Exception as e:
            error_msg = f"Error during formatting: {str(e)}"
            print("[TextCache]", error_msg)
            self.notification.update_status(error_msg)
            play_sound("error")
        finally:
            self.is_formatting = False
            self._update_status()

    def _format_with_api(self, text_to_format, format_type, original_text):
        """Format text using the Gemini API."""
        if not self.api_key:
            error_msg = (
                "Gemini API key not set! Provide it in config.toml or environment."
            )
            print("[TextCache]", error_msg)
            self.notification.update_status(error_msg)
            return

        prompt = self.config["formatting_prompts"][format_type] + text_to_format
        print(f"[TextCache] Formatting with prompt: '{prompt[:70]}...'")

        formatted_text = generate_gemini(
            prompt, self.api_key, self.config["api"]["model"]
        )

        print(
            f"[TextCache] Formatted text (first 50 chars): '{formatted_text[:50]}...'"
        )

        self.last_unformatted_text = text_to_format
        self.last_format_used = format_type
        self.last_formatted_text = formatted_text

        # If we formatted the actual cache text, we consider that chunk done
        if original_text == self.cache:
            self.cache = ""

        self.notification.show_format_result(formatted_text)
        self._paste_direct(formatted_text, is_formatted=True)

        prompt = self.config["formatting_prompts"][format_type] + text_to_format
        print(f"[TextCache] Formatting with prompt: '{prompt[:70]}...'")

        formatted_text = generate_gemini(
            prompt, self.api_key, self.config["api"]["model"]
        )

        print(
            f"[TextCache] Formatted text (first 50 chars): '{formatted_text[:50]}...'"
        )

        self.last_unformatted_text = text_to_format
        self.last_format_used = format_type
        self.last_formatted_text = formatted_text

        # If we formatted the actual cache text, we consider that chunk done
        if original_text == self.cache:
            self.cache = ""

        self.notification.show_format_result(formatted_text)
        self._paste_direct(formatted_text, is_formatted=True)

    def _paste_direct(self, text, is_formatted):
        """
        Paste text directly without clearing the cache.
        """
        try:
            self._perform_paste_operation(text)
            play_sound("paste_formatted" if is_formatted else "paste_raw")
            print(f"[TextCache] Pasted {'formatted' if is_formatted else 'raw'} text.")
        except Exception as e:
            print(f"[TextCache] Error pasting text: {e}")

    # def _perform_paste_operation(self, text):
    #     """Common code for pasting text via clipboard."""
    #     try:
    #         original_clipboard = pyperclip.paste()
    #         pyperclip.copy(text)
    #         time.sleep(0.05)
    #         pyautogui.keyDown("ctrl")
    #         pyautogui.press("v")
    #         pyautogui.keyUp("ctrl")
    #         time.sleep(0.05)
    #         pyperclip.copy(original_clipboard)
    #     except Exception as e:
    #         print(f"Paste operation error: {e}")
    #         self.notification.update_status(f"Paste error: {e}")


    def _perform_paste_operation(self, text):
        try:
            original_clipboard = pyperclip.paste()
            pyperclip.copy(text)

            # Tweak this sleep to something smaller – or remove it entirely
            # if you find that your system doesn't need the delay.
            time.sleep(0.05)  

            # Option A: Use keyboard lib
            import keyboard
            keyboard.press_and_release('ctrl+v')

            # Option B: Or use pyautogui.hotkey which handles press + release:
            # pyautogui.hotkey('ctrl', 'v')

            # If you can safely remove or reduce the second sleep, do so:
            time.sleep(0.03)

            pyperclip.copy(original_clipboard)

        except Exception as e:
            print(f"Paste operation error: {e}")
            self.notification.update_status(f"Paste error: {e}")


    def _update_status(self):
        """Update status bar with current state information."""
        status_parts = []
        if self.cache.strip():
            words = len(self.cache.strip().split())
            status_parts.append(f"Cache: {words} words")
        else:
            status_parts.append("Cache: Empty")

        if self.is_formatting:
            status_parts.append("Formatting...")
        elif self.is_pasting:
            status_parts.append("Pasting...")

        format_type = self.notification.get_current_format()
        status_parts.append(f"Format: {format_type}")

        final_status = " | ".join(status_parts)
        self.notification.update_status(final_status)

    def cleanup(self):
        """Clean up resources before exit."""
        self.notification.cleanup()
