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
    Checkbutton,
)

from speak_now.app import SpeechTranscriptionApp

# ---------------------------------------------------------------------
# CONFIGURATION MANAGEMENT
# ---------------------------------------------------------------------

CONFIG_FILE = "stt_config.toml"


# ---------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------
def main():
    app = SpeechTranscriptionApp(CONFIG_FILE)
    app.start()


if __name__ == "__main__":
    main()
