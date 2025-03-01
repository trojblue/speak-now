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
CONFIG_FILE = "stt_config.toml"

DEFAULT_CONFIG = {
    "api": {
        "gemini_api_key": "",  # Will also check environment variable
        "model": "gemini-1.5-flash"
    },
    "stt": {
        "model": "large-v2",
        "timeout": 1.0
    },
    "hotkeys": {
        "paste_raw": "ctrl+`",
        "paste_formatted": "alt+`", 
        "toggle_recording": "ctrl+alt+space"
    },
    "ui": {
        "opacity": 0.90,
        "max_history_items": 10,
        "default_format": "Concise"
    },
    "formatting_prompts": {
        "Natural": "Reformat this transcription to sound more natural and fix any grammar issues: ",
        "Formal": "Reformat this transcription into formal, professional language: ",
        "Concise": "Reformat this transcription to be more concise while preserving all important information: ",
        "Catgirl": "Reformat this transcription to sound like a cute catgirl talking: ",
        "None": ""  # No formatting
    }
}

def load_config():
    """Load configuration from file or create default if not exists"""
    try:
        if os.path.exists(CONFIG_FILE):
            config = toml.load(CONFIG_FILE)
            # Merge with defaults for any missing keys
            merged_config = DEFAULT_CONFIG.copy()
            for section in config:
                if section in merged_config:
                    merged_config[section].update(config[section])
                else:
                    merged_config[section] = config[section]
            return merged_config
        else:
            # Save default config for future use
            with open(CONFIG_FILE, 'w') as f:
                toml.dump(DEFAULT_CONFIG, f)
            return DEFAULT_CONFIG
    except Exception as e:
        print(f"Error loading config: {e}. Using defaults.")
        return DEFAULT_CONFIG

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

# ---------------------------------------------------------------------
# GUI NOTIFICATION CLASS
# ---------------------------------------------------------------------
class EnhancedNotification:
    """Thread-safe, draggable notification with formatting controls and status display."""
    
    def __init__(self, format_callback, config):
        self.message_queue = queue.Queue()
        self.format_callback = format_callback
        self.current_text = ""
        self.history = []  # Store history items
        self.config = config
        self.recording_active = True  # Start with recording enabled

        self.root = None
        self.popup = None
        self.content_label = None
        self.status_label = None
        self.format_var = None
        self.history_listbox = None
        
        self.running = False
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()
        time.sleep(0.1)

    def _run_gui(self):
        """Initialize and run the GUI in a separate thread."""
        try:
            self.root = Tk()
            self.root.withdraw()
            self.format_var = StringVar(self.root)
            self.format_var.set(self.config["ui"]["default_format"])

            self._setup_main_window()
            self._setup_title_bar()
            self._setup_content_area()
            self._setup_history_panel()
            self._setup_controls()
            self._setup_status_bar()
            
            # Set size and center
            self.popup.geometry("400x320")
            self._center_window()

            self.running = True
            self._process_queue()
            self.root.mainloop()
        except Exception as e:
            print(f"GUI thread error: {e}")

    def _setup_main_window(self):
        """Setup the main popup window."""
        self.popup = Toplevel(self.root)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)
        self.popup.attributes("-alpha", self.config["ui"]["opacity"])
        self.popup.configure(bg="#333333")

        # Main frame
        self.main_frame = Frame(self.popup, bg="#333333")
        self.main_frame.pack(fill="both", expand=True)

    def _setup_title_bar(self):
        """Setup the custom title bar with drag functionality."""
        title_bar = Frame(self.main_frame, bg="#222222")
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
        
        # Recording toggle button
        self.recording_var = BooleanVar(value=True)
        self.recording_button = Button(
            title_bar, 
            text="⏸️",  # Pause symbol
            font=("Segoe UI", 10),
            fg="#FFFFFF", 
            bg="#222222",
            bd=0, 
            padx=8, 
            pady=5,
            activebackground="#555555", 
            activeforeground="#FFFFFF",
            command=self._toggle_recording
        )
        self.recording_button.pack(side="right", padx=(0, 5))
        
        # Minimize button
        min_button = Button(
            title_bar, 
            text="_",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF", 
            bg="#222222",
            bd=0, 
            padx=8, 
            pady=5,
            activebackground="#555555", 
            activeforeground="#FFFFFF",
            command=self._minimize_window
        )
        min_button.pack(side="right", padx=(0, 5))
        
        # Close button
        close_button = Button(
            title_bar, 
            text="×",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF", 
            bg="#222222",
            bd=0, 
            padx=10, 
            pady=5,
            activebackground="#FF5555", 
            activeforeground="#FFFFFF",
            command=self._close_window
        )
        close_button.pack(side="right")

        # Make title bar draggable
        self._make_draggable(title_bar, title_label)

    def _setup_content_area(self):
        """Setup the main content area to display the current transcription."""
        content_frame = Frame(self.main_frame, bg="#333333", padx=15, pady=10)
        content_frame.pack(fill="both", expand=True)

        self.content_label = Label(
            content_frame,
            text="Waiting for speech...",
            font=("Segoe UI", 9),
            fg="#FFFFFF",
            bg="#333333",
            wraplength=370,
            justify="left",
            anchor="w"
        )
        self.content_label.pack(fill="both", expand=True, pady=(0, 10))

    def _setup_history_panel(self):
        """Setup the history panel to display previous transcriptions."""
        history_frame = Frame(self.main_frame, bg="#2A2A2A", padx=15, pady=5)
        history_frame.pack(fill="x", side="bottom", before=self.content_label)
        
        history_label = Label(
            history_frame,
            text="Recent Transcriptions:",
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg="#2A2A2A"
        )
        history_label.pack(anchor="w", pady=(0, 5))
        
        list_frame = Frame(history_frame, bg="#2A2A2A")
        list_frame.pack(fill="x", expand=True)
        
        self.history_listbox = Listbox(
            list_frame,
            height=3,
            font=("Segoe UI", 8),
            fg="#DDDDDD",
            bg="#3A3A3A",
            selectbackground="#505050",
            bd=0,
            highlightthickness=1,
            highlightcolor="#444444"
        )
        self.history_listbox.pack(side="left", fill="x", expand=True)
        self.history_listbox.bind("<Double-1>", self._on_history_item_select)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.history_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.history_listbox.yview)

    def _setup_controls(self):
        """Setup the control panel with formatting options and paste buttons."""
        controls_frame = Frame(self.main_frame, bg="#333333", padx=15, pady=8)
        controls_frame.pack(fill="x", side="bottom")
        
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
            *self.config["formatting_prompts"].keys()
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

        raw_button = Button(
            controls_frame,
            text=f"Paste Raw ({self.config['hotkeys']['paste_raw']})",
            font=("Segoe UI", 9),
            fg="#FFFFFF",
            bg="#555555",
            activebackground="#666666",
            bd=0, padx=8, pady=2,
            command=self._request_raw_paste
        )
        raw_button.pack(side="right", padx=(10, 0))

        format_button = Button(
            controls_frame,
            text=f"Format & Paste ({self.config['hotkeys']['paste_formatted']})",
            font=("Segoe UI", 9),
            fg="#FFFFFF",
            bg="#007ACC",
            activebackground="#0066AA",
            bd=0, padx=8, pady=2,
            command=self._request_formatting
        )
        format_button.pack(side="right")

    def _setup_status_bar(self):
        """Setup the status bar at the bottom of the window."""
        status_frame = Frame(self.main_frame, bg="#222222", padx=10, pady=5)
        status_frame.pack(fill="x", side="bottom")
        
        self.status_label = Label(
            status_frame,
            text="Cache: Empty | Format: None",
            font=("Segoe UI", 8),
            fg="#AAAAAA",
            bg="#222222"
        )
        self.status_label.pack(side="left")

    def _make_draggable(self, widget, title_label):
        """Make a widget draggable (for custom window)."""
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
        """Center the window on the screen."""
        if self.popup:
            self.popup.update_idletasks()
            width = self.popup.winfo_width()
            height = self.popup.winfo_height()
            x = (self.popup.winfo_screenwidth() // 2) - (width // 2)
            y = (self.popup.winfo_screenheight() // 2) - (height // 2)
            self.popup.geometry(f"{width}x{height}+{x}+{y}")

    def _minimize_window(self):
        """Minimize the window."""
        if self.popup:
            self.popup.withdraw()

    def _close_window(self):
        """Close the application."""
        if self.root:
            self.running = False
            self.root.quit()

    def _show_window(self):
        """Show the window if it was minimized."""
        if self.popup:
            self.popup.deiconify()
            self.popup.lift()
            self.popup.attributes("-topmost", True)

    def _toggle_recording(self):
        """Toggle recording on/off."""
        self.recording_active = not self.recording_active
        
        if self.recording_active:
            self.recording_button.config(text="⏸️")  # Pause symbol
            self.update_status("Recording active")
        else:
            self.recording_button.config(text="▶️")  # Play symbol
            self.update_status("Recording paused")
            
        play_sound("toggle_recording")
        
    def _process_queue(self):
        """Process messages from the queue to update the UI."""
        if not self.running or not self.content_label:
            return
            
        try:
            while not self.message_queue.empty():
                message_type, message = self.message_queue.get_nowait()
                
                if message_type == "content":
                    # Display the most recent part of long text instead of the beginning
                    if len(message) > 200:
                        # Keep the last 200 characters for display
                        display_message = "..." + message[-197:]
                    else:
                        display_message = message
                        
                    self.current_text = message
                    self.content_label.config(text=display_message)
                    self._show_window()
                    
                elif message_type == "status":
                    self.status_label.config(text=message)
                    
                elif message_type == "format_result":
                    if len(message) > 200:
                        display_message = "..." + message[-197:]
                    else:
                        display_message = message
                        
                    self.current_text = message
                    self.content_label.config(text=display_message)
                    self.status_label.config(text="Formatting complete")
                    self._show_window()
                    
                elif message_type == "add_history":
                    # Add to history if significant (more than 5 words)
                    if len(message.split()) > 5:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        # Create a preview (first few words)
                        words = message.split()
                        preview = " ".join(words[:4]) + ("..." if len(words) > 4 else "")
                        history_item = f"[{timestamp}] {preview}"
                        
                        # Add to our internal history list
                        self.history.insert(0, {"time": timestamp, "text": message, "preview": history_item})
                        
                        # Keep history within limit
                        if len(self.history) > self.config["ui"]["max_history_items"]:
                            self.history.pop()
                            
                        # Update listbox
                        self.history_listbox.delete(0, "end")
                        for item in self.history:
                            self.history_listbox.insert("end", item["preview"])

            self.root.after(100, self._process_queue)
        except Exception as e:
            print(f"Error processing queue: {e}")
            self.root.after(100, self._process_queue)

    def _on_history_item_select(self, event):
        """Handle double-click on history item."""
        if self.history_listbox.curselection():
            index = self.history_listbox.curselection()[0]
            if 0 <= index < len(self.history):
                self.current_text = self.history[index]["text"]
                self.content_label.config(text=self.current_text)

    def show_content(self, message):
        """Show content in the UI and add to history."""
        if self.running:
            self.message_queue.put(("content", message))
            self.message_queue.put(("add_history", message))

    def update_status(self, message):
        """Update the status bar."""
        if self.running:
            self.message_queue.put(("status", message))
    
    def show_format_result(self, message):
        """Show formatted text result."""
        if self.running:
            self.message_queue.put(("format_result", message))
    
    def _request_formatting(self):
        """Called by the GUI 'Format & Paste' button."""
        if self.current_text:
            format_type = self.format_var.get()
            self.format_callback(self.current_text, format_type)
        else:
            self.update_status("Nothing to format - cache is empty")
            
    def _request_raw_paste(self):
        """Called by the GUI 'Paste Raw' button."""
        if hasattr(self, 'raw_paste_callback'):
            self.raw_paste_callback()
        else:
            self.update_status("Raw paste callback not set")

    def set_raw_paste_callback(self, callback):
        """Set callback for raw paste button."""
        self.raw_paste_callback = callback

    def get_current_format(self):
        """Get currently selected format type."""
        return self.format_var.get()
        
    def is_recording_enabled(self):
        """Check if recording is currently enabled."""
        return self.recording_active

    def cleanup(self):
        """Clean up resources before exit."""
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
    def __init__(self, config):
        self.cache = ""                # Current text in memory
        self.previous_raw = ""         # Last raw text that was pasted
        self.last_unformatted_text = ""
        self.last_formatted_text = ""
        self.last_format_used = None
        self.config = config
        
        self.is_pasting = False
        self.is_formatting = False
        self.lock = threading.Lock()

        self.notification = EnhancedNotification(
            format_callback=self.format_and_paste,
            config=config
        )
        self.notification.set_raw_paste_callback(self.paste_and_clear)
        
        self.api_key = self.config["api"]["gemini_api_key"] or os.environ.get("GEMINI_API_KEY", "")

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
        print(f"[TextCache] Hotkey triggered: {self.config['hotkeys']['paste_raw']} (raw paste)")
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
        print(f"[TextCache] Hotkey triggered: {self.config['hotkeys']['paste_formatted']} (format & paste)")
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
            same_unformatted = (text_to_format == self.last_unformatted_text)
            same_format = (format_type == self.last_format_used)

            if same_unformatted and same_format and self.last_formatted_text:
                print("[TextCache] Reusing previously formatted text (no new LLM call).")
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
            error_msg = "Gemini API key not set! Provide it in config.toml or environment."
            print("[TextCache]", error_msg)
            self.notification.update_status(error_msg)
            return

        prompt = self.config["formatting_prompts"][format_type] + text_to_format
        print(f"[TextCache] Formatting with prompt: '{prompt[:70]}...'")
        
        formatted_text = generate_gemini(
            prompt, 
            self.api_key, 
            self.config["api"]["model"]
        )
        
        print(f"[TextCache] Formatted text (first 50 chars): '{formatted_text[:50]}...'")

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

    def _perform_paste_operation(self, text):
        """Common code for pasting text via clipboard."""
        try:
            original_clipboard = pyperclip.paste()
            pyperclip.copy(text)
            time.sleep(0.1)
            pyautogui.keyDown('ctrl')
            pyautogui.press('v')
            pyautogui.keyUp('ctrl')
            time.sleep(0.1)
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
        self.config = load_config()
        
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