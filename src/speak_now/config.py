import os
import toml


DEFAULT_CONFIG = {
    "api": {
        "gemini_api_key": "",  # Will also check environment variable
        "model": "gemini-1.5-flash",
    },
    "stt": {"model": "large-v2", "timeout": 1.0},
    "hotkeys": {
        "paste_raw": "ctrl+`",
        "paste_formatted": "alt+`",
        "toggle_recording": "ctrl+alt+space",
    },
    "ui": {"opacity": 0.90, "max_history_items": 10, "default_format": "Concise"},
    "formatting_prompts": {
        "Natural": "Reformat this transcription to sound more natural and fix any grammar issues: ",
        "Formal": "Reformat this transcription into formal, professional language: ",
        "Concise": "Reformat this transcription to be more concise while preserving all important information: ",
        "Catgirl": "Reformat this transcription to sound like a cute catgirl talking: ",
        "None": "",  # No formatting
    },
}


def load_config(CONFIG_FILE):
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
            with open(CONFIG_FILE, "w") as f:
                toml.dump(DEFAULT_CONFIG, f)
            return DEFAULT_CONFIG
    except Exception as e:
        print(f"Error loading config: {e}. Using defaults.")
        return DEFAULT_CONFIG
