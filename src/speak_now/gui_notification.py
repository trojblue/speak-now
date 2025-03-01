import queue
import threading
import time
from datetime import datetime
from tkinter import (
    Tk,
    Toplevel,
    Label,
    Frame,
    Button,
    OptionMenu,
    StringVar,
    Scrollbar,
    Listbox,
    BooleanVar,
)
from .utils import play_sound


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
            
            # Hide window on startup if configured
            if self.config["ui"].get("start_hidden", False):
                self.popup.withdraw()

            self.running = True
            self._process_queue()
            self.root.mainloop()
        except Exception as e:
            print(f"GUI thread error: {e}")

    def toggle_window_visibility(self):
        """Toggle window visibility state."""
        if self.popup:
            if self.popup.state() == 'withdrawn':
                self._show_window()
                self.update_status("Window shown")
            else:
                self.popup.withdraw()
                self.update_status("Window hidden")
            play_sound("toggle_recording")

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
            padx=10,
            pady=5,
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
            command=self._toggle_recording,
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
            command=self._minimize_window,
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
            command=self._close_window,
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
            anchor="w",
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
            bg="#2A2A2A",
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
            highlightcolor="#444444",
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
            bg="#333333",
        )
        format_label.pack(side="left", padx=(0, 5))

        format_menu = OptionMenu(
            controls_frame, self.format_var, *self.config["formatting_prompts"].keys()
        )
        format_menu.config(
            font=("Segoe UI", 9),
            bg="#444444",
            fg="#FFFFFF",
            activebackground="#555555",
            activeforeground="#FFFFFF",
            highlightthickness=0,
            bd=0,
        )
        format_menu["menu"].config(
            bg="#444444",
            fg="#FFFFFF",
            activebackground="#555555",
            activeforeground="#FFFFFF",
        )
        format_menu.pack(side="left", padx=(0, 10))

        raw_button = Button(
            controls_frame,
            text=f"Paste Raw ({self.config['hotkeys']['paste_raw']})",
            font=("Segoe UI", 9),
            fg="#FFFFFF",
            bg="#555555",
            activebackground="#666666",
            bd=0,
            padx=8,
            pady=2,
            command=self._request_raw_paste,
        )
        raw_button.pack(side="right", padx=(10, 0))

        format_button = Button(
            controls_frame,
            text=f"Format & Paste ({self.config['hotkeys']['paste_formatted']})",
            font=("Segoe UI", 9),
            fg="#FFFFFF",
            bg="#007ACC",
            activebackground="#0066AA",
            bd=0,
            padx=8,
            pady=2,
            command=self._request_formatting,
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
            bg="#222222",
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
                        preview = " ".join(words[:4]) + (
                            "..." if len(words) > 4 else ""
                        )
                        history_item = f"[{timestamp}] {preview}"

                        # Add to our internal history list
                        self.history.insert(
                            0,
                            {
                                "time": timestamp,
                                "text": message,
                                "preview": history_item,
                            },
                        )

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
        if hasattr(self, "raw_paste_callback"):
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
