#!/usr/bin/env python3
import os
import sys
import argparse
from speak_now.app import SpeechTranscriptionApp

def main():
    """
    Command-line interface for Speak Now.
    
    Handles command-line arguments and launches the application
    with the appropriate configuration.
    """
    parser = argparse.ArgumentParser(
        description="Speak Now - Low-latency speech-to-text with AI formatting",
        epilog="For more information, visit: https://github.com/yourusername/speak-now"
    )
    
    parser.add_argument(
        "-c", "--config",
        dest="config_file",
        default="stt_config.toml",
        help="Path to configuration file (default: stt_config.toml)"
    )

    parser.add_argument(
        "--hidden",
        action="store_true",
        help="Start with UI hidden (overrides config setting)"
    )
    
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if config file exists
    if not os.path.exists(args.config_file):
        print(f"Notice: Config file '{args.config_file}' not found. Using default configuration.")
    else:
        print(f"Using config file: {args.config_file}")
    try:
        # Initialize and start the application
        app = SpeechTranscriptionApp(args.config_file)
        
        # If --hidden flag was used, override the config setting
        if args.hidden and hasattr(app, 'config') and 'ui' in app.config:
            app.config['ui']['start_hidden'] = True
            print("Starting with UI hidden (command-line override)")
        
        # Start the application
        app.start()
        
    except KeyboardInterrupt:
        print("\nExiting Speak Now...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    cli_main()