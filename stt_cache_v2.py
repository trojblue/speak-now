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
