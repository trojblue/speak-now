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

from tkinter import Tk, Toplevel, Label, Frame, Button, OptionMenu, StringVar

# ---------------------------------------------------------------------
# CONFIGURATION & CONSTANTS
# ---------------------------------------------------------------------
CONFIG = {
    "gemini_api_key": "",  # or use environment variable
    "formatting_prompts": {
        "Natural": "Reformat this transcription to sound more natural and fix any grammar issues: ",
        "Formal": "Reformat this transcription into formal, professional language: ",
        "Concise": "Reformat this transcription to be more concise while preserving all important information: ",
        "Catgirl": "Reformat this transcription to sound like a cute catgirl talking: ",
        "None": ""  # No formatting
    }
}

# ---------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------
def generate_gemini(prompt, api_key, model="gemini-1.5-flash"):
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
    except:
        pass

# ---------------------------------------------------------------------
# GUI NOTIFICATION CLASS
# ---------------------------------------------------------------------
class EnhancedNotification:
    """Thread-safe, draggable notification with formatting controls and status display."""
    
    def __init__(self, format_callback):
        self.message_queue = queue.Queue()
        self.format_callback = format_callback
        self.current_text = ""

        self.root = None
        self.popup = None
        self.content_label = None
        self.status_label = None
        self.format_var = None
        
        self.running = False
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()
        time.sleep(0.1)

    def _run_gui(self):
        try:
            self.root = Tk()
            self.root.withdraw()
            self.format_var = StringVar(self.root)
            self.format_var.set("Concise")  # Default format

            self.popup = Toplevel(self.root)
            self.popup.overrideredirect(True)
            self.popup.attributes("-topmost", True)
            self.popup.attributes("-alpha", 0.90)
            self.popup.configure(bg="#333333")

            main_frame = Frame(self.popup, bg="#333333")
            main_frame.pack(fill="both", expand=True)

            # Title bar
            title_bar = Frame(main_frame, bg="#222222")
            title_bar.pack(fill="x", side="top")
            
            title_label = Label(
                title_bar,
                text="Speech Transcription",
                font=("Segoe UI", 10, "bold"),
                fg="#FFFFFF",
                bg="#222222",
                padx=10, pady=5
            )
            title_label.pack(side="left")
            
            close_button = Button(
                title_bar, text="×",
                font=("Segoe UI", 10, "bold"),
                fg="#FFFFFF", bg="#222222",
                bd=0, padx=10, pady=5,
                activebackground="#FF5555", activeforeground="#FFFFFF",
                command=self._minimize_window
            )
            close_button.pack(side="right")

            # Content frame
            content_frame = Frame(main_frame, bg="#333333", padx=15, pady=10)
            content_frame.pack(fill="both", expand=True)

            self.content_label = Label(
                content_frame,
                text="Waiting for speech...",
                font=("Segoe UI", 9),
                fg="#FFFFFF",
                bg="#333333",
                wraplength=280,
                justify="left",
                anchor="w"
            )
            self.content_label.pack(fill="both", expand=True, pady=(0, 10))

            # Status bar
            status_frame = Frame(main_frame, bg="#222222", padx=10, pady=5)
            status_frame.pack(fill="x", side="bottom")
            
            self.status_label = Label(
                status_frame,
                text="Cache: Empty | Format: None",
                font=("Segoe UI", 8),
                fg="#AAAAAA",
                bg="#222222"
            )
            self.status_label.pack(side="left")

            # Controls frame
            controls_frame = Frame(main_frame, bg="#333333", padx=15, pady=8)
            controls_frame.pack(fill="x", side="bottom", before=status_frame)
            
            format_label = Label(
                controls_frame,
                text="Format:",
                font=("Segoe UI", 9),
                fg="#FFFFFF",
                bg="#333333"
            )
            format_label.pack(side="left", padx=(0, 5))
            
            format_menu = OptionMenu(
                controls_frame,
                self.format_var,
                *CONFIG["formatting_prompts"].keys()
            )
            format_menu.config(
                font=("Segoe UI", 9),
                bg="#444444",
                fg="#FFFFFF",
                activebackground="#555555",
                activeforeground="#FFFFFF",
                highlightthickness=0,
                bd=0
            )
            format_menu["menu"].config(
                bg="#444444",
                fg="#FFFFFF",
                activebackground="#555555",
                activeforeground="#FFFFFF"
            )
            format_menu.pack(side="left", padx=(0, 10))

            format_button = Button(
                controls_frame,
                text="Format & Paste (alt+`)",
                font=("Segoe UI", 9),
                fg="#FFFFFF",
                bg="#007ACC",
                activebackground="#0066AA",
                bd=0, padx=8, pady=2,
                command=self._request_formatting
            )
            format_button.pack(side="right")

            # Set size and center
            self.popup.geometry("350x200")
            self._center_window()

            self._make_draggable(title_bar, title_label)

            self.running = True
            self._process_queue()
            self.root.mainloop()

        except Exception as e:
            print(f"GUI thread error: {e}")

    def _make_draggable(self, widget, title_label):
        self._drag_data = {"x": 0, "y": 0}
        
        def start_drag(event):
            self._drag_data["x"] = event.x
            self._drag_data["y"] = event.y

        def drag(event):
            deltax = event.x - self._drag_data["x"]
            deltay = event.y - self._drag_data["y"]
            x = self.popup.winfo_x() + deltax
            y = self.popup.winfo_y() + deltay
            self.popup.geometry(f"+{x}+{y}")

        def stop_drag(event):
            self._drag_data["x"] = 0
            self._drag_data["y"] = 0

        widget.bind("<Button-1>", start_drag)
        widget.bind("<B1-Motion>", drag)
        widget.bind("<ButtonRelease-1>", stop_drag)
        title_label.bind("<Button-1>", start_drag)
        title_label.bind("<B1-Motion>", drag)
        title_label.bind("<ButtonRelease-1>", stop_drag)

    def _center_window(self):
        if self.popup:
            self.popup.update_idletasks()
            width = self.popup.winfo_width()
            height = self.popup.winfo_height()
            x = (self.popup.winfo_screenwidth() // 2) - (width // 2)
            y = (self.popup.winfo_screenheight() // 2) - (height // 2)
            self.popup.geometry(f"{width}x{height}+{x}+{y}")

    def _minimize_window(self):
        if self.popup:
            self.popup.withdraw()

    def _show_window(self):
        if self.popup:
            self.popup.deiconify()
            self.popup.lift()
            self.popup.attributes("-topmost", True)

    def _process_queue(self):
        if not self.running or not self.content_label:
            return
        try:
            while not self.message_queue.empty():
                message_type, message = self.message_queue.get_nowait()
                
                if message_type == "content":
                    if len(message) > 150:
                        display_message = message[:147] + "..."
                    else:
                        display_message = message
                    self.current_text = message
                    self.content_label.config(text=display_message)
                    self._show_window()
                    
                elif message_type == "status":
                    self.status_label.config(text=message)
                    
                elif message_type == "format_result":
                    if len(message) > 150:
                        display_message = message[:147] + "..."
                    else:
                        display_message = message
                    self.current_text = message
                    self.content_label.config(text=display_message)
                    self.status_label.config(text="Formatting complete")
                    self._show_window()

            self.root.after(100, self._process_queue)
        except Exception as e:
            print(f"Error processing queue: {e}")

    def show_content(self, message):
        if self.running:
            self.message_queue.put(("content", message))

    def update_status(self, message):
        if self.running:
            self.message_queue.put(("status", message))
    
    def show_format_result(self, message):
        if self.running:
            self.message_queue.put(("format_result", message))
    
    def _request_formatting(self):
        """Called by the GUI 'Format & Paste (alt+`)' button."""
        if self.current_text:
            format_type = self.format_var.get()
            self.format_callback(self.current_text, format_type)
        else:
            self.update_status("Nothing to format - cache is empty")

    def get_current_format(self):
        return self.format_var.get()

    def cleanup(self):
        self.running = False
        if self.root:
            try:
                self.root.quit()
                self.root.update()
                self.root.destroy()
            except Exception:
                pass

# ---------------------------------------------------------------------
# TEXT CACHE (CORE LOGIC)
# ---------------------------------------------------------------------
class TextCache:
    def __init__(self):
        self.cache = ""                # Current text in memory
        self.previous_raw = ""         # Last raw text that was pasted
        self.last_unformatted_text = ""
        self.last_formatted_text = ""
        self.last_format_used = None

        self.is_pasting = False
        self.is_formatting = False
        self.lock = threading.Lock()

        self.notification = EnhancedNotification(format_callback=self.format_and_paste)
        
        self.api_key = CONFIG["gemini_api_key"] or os.environ.get("GEMINI_API_KEY", "")

    def add_text(self, text):
        """
        Add recognized speech to the text cache. 
        **Important**: We remove the check that blocks new text if is_pasting or is_formatting.
        """
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
        print("[TextCache] Hotkey triggered: ctrl+` (raw paste)")
        with self.lock:
            text_to_paste = self.cache.strip() if self.cache.strip() else self.previous_raw

            if not text_to_paste:
                print("[TextCache] Nothing to paste (empty cache + no previous raw).")
                play_sound("error")
                self.notification.update_status("Cache is empty, nothing to paste")
                return

            self.is_pasting = True
            try:
                self._update_status()
                original_clipboard = pyperclip.paste()

                # If new text is in the cache, update previous_raw
                if self.cache.strip():
                    self.previous_raw = text_to_paste

                self.cache = ""  # Clear it now that we have “finished” that chunk.

                # Actually paste
                pyperclip.copy(text_to_paste)
                time.sleep(0.1)
                pyautogui.keyDown('ctrl')
                pyautogui.press('v')
                pyautogui.keyUp('ctrl')

                play_sound("paste_raw")
                self.notification.update_status("Text pasted! Cache cleared.")
                print(f"[TextCache] Pasted raw text: '{text_to_paste}'")

                time.sleep(0.1)
                pyperclip.copy(original_clipboard)

            finally:
                self.is_pasting = False
                self._update_status()

    def format_and_paste(self, text=None, format_type=None):
        """
        Format the text using Gemini (if needed) and then paste. 
        If user spams alt+`, we only re-run LLM if text or format changed.
        """
        print("[TextCache] Hotkey triggered: alt+` (format & paste)")
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

            self.is_formatting = True
            try:
                play_sound("processing")
                self._update_status()
                self.notification.update_status(f"Formatting with {format_type}...")

                # If we are formatting new text from the cache, set previous_raw
                if text == self.cache and self.cache.strip():
                    self.previous_raw = text_to_format

                # Check if we can reuse a previous format
                same_unformatted = (text_to_format == self.last_unformatted_text)
                same_format = (format_type == self.last_format_used)

                if same_unformatted and same_format and self.last_formatted_text:
                    print("[TextCache] Reusing previously formatted text (no new LLM call).")
                    formatted_text = self.last_formatted_text
                    self.notification.show_format_result(formatted_text)
                    self._paste_direct(formatted_text, is_formatted=True)
                else:
                    # Actually call the LLM
                    if not self.api_key:
                        error_msg = "Gemini API key not set! Provide it in CONFIG or environment."
                        print("[TextCache]", error_msg)
                        self.notification.update_status(error_msg)
                        return

                    prompt = CONFIG["formatting_prompts"][format_type] + text_to_format
                    print(f"[TextCache] Formatting with prompt: '{prompt[:70]}...'")
                    formatted_text = generate_gemini(prompt, self.api_key)
                    print(f"[TextCache] Formatted text (first 50 chars): '{formatted_text[:50]}...'")

                    self.last_unformatted_text = text_to_format
                    self.last_format_used = format_type
                    self.last_formatted_text = formatted_text

                    # If we formatted the actual cache text, we consider that chunk done
                    if text == self.cache:
                        self.cache = ""

                    self.notification.show_format_result(formatted_text)
                    self._paste_direct(formatted_text, is_formatted=True)

            except Exception as e:
                error_msg = f"Error during formatting: {str(e)}"
                print("[TextCache]", error_msg)
                self.notification.update_status(error_msg)
                play_sound("error")
            finally:
                self.is_formatting = False
                self._update_status()

    def _paste_direct(self, text, is_formatted):
        """
        Paste text directly without clearing the cache 
        (so the user can keep appending if they want).
        """
        try:
            original_clipboard = pyperclip.paste()
            pyperclip.copy(text)
            time.sleep(0.1)
            pyautogui.keyDown('ctrl')
            pyautogui.press('v')
            pyautogui.keyUp('ctrl')
            play_sound("paste_formatted" if is_formatted else "paste_raw")
            print(f"[TextCache] Pasted {'formatted' if is_formatted else 'raw'} text.")
            time.sleep(0.1)
            pyperclip.copy(original_clipboard)
        except Exception as e:
            print(f"[TextCache] Error pasting text: {e}")

    def _update_status(self):
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
        self.notification.cleanup()

# ---------------------------------------------------------------------
# MAIN APPLICATION LOGIC
# ---------------------------------------------------------------------
def setup_hotkeys(text_cache):
    """
    Setup hotkeys for paste (Ctrl+`) and format & paste (Alt+`).
    Removed 'suppress=True, timeout=1.0' to avoid losing keystrokes.
    """
    keyboard.add_hotkey("ctrl+`", text_cache.paste_and_clear)
    keyboard.add_hotkey("alt+`",  lambda: text_cache.format_and_paste())

def main():
    print("Enhanced Speech-to-Text with AI Formatting.")
    print("Speak to add text to the cache.")
    print("Hotkeys:")
    print("  Ctrl+` => Paste text (no formatting).")
    print("  Alt+`  => Format & Paste text.")
    print("Use the GUI window to select formatting style manually.")
    print("Press Ctrl+C here to exit anytime.\n")

    from RealtimeSTT import AudioToTextRecorder

    text_cache = TextCache()
    setup_hotkeys(text_cache)

    # Create the audio recorder (your RealtimeSTT class).
    recorder = AudioToTextRecorder(model="large-v2")
    recorder.timeout = 1  # Adjust as needed
    play_sound("startup")

    try:
        while True:
            # Continuously capture speech and add to cache
            recorder.text(lambda recognized_text: text_cache.add_text(recognized_text))
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n[Main] Exiting by user request...")
    finally:
        try:
            recorder.shutdown()
        except:
            pass
        keyboard.unhook_all()
        text_cache.cleanup()
        sys.exit(0)

if __name__ == '__main__':
    main()
