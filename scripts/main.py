def main():
    from . import dependencies
    dependencies.check_and_install_libraries()

    from . import VoskService
    from . import AudioService
    from . import TranscriptionService

    print("Voice Commander v0.2.3\n")
    print("Usage: vc [--llm] [-d DEVICE_INDEX_OR_NAME] [-v | --verbose]\n"
              "Press Ctrl+C to stop recording and transcribing. The transcribed text will be copied to the clipboard.\n")

    import argparse
    from . import config
    parser = argparse.ArgumentParser(description="Voice Commander")
    parser.add_argument("--llm", action="store_true", help="Enable LLM processing")
    parser.add_argument("-d", "--device", help="Audio input device index or name substring to use")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    config.USE_LLM = args.llm
    config.VERBOSE_OUTPUT = args.verbose

    # Configure logging levels based on verbose flag
    if not config.VERBOSE_OUTPUT:
        import logging
        # Set higher log level for common verbose modules
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('KeyboardService').setLevel(logging.WARNING)

    vosk_service = VoskService.VoskService()
    
    # Initialize audio service with device index or name if provided
    device_input = args.device
    # Try to convert to int if it's a number, otherwise keep as string
    device_param = None
    if device_input is not None:
        try:
            device_param = int(device_input)
        except ValueError:
            device_param = device_input
    
    audio_service = AudioService.AudioService(device_param)
    
    transcription_service = TranscriptionService.TranscriptionService(vosk_service, audio_service)
    
    transcription_service.Transcribe()

if __name__ == "__main__":
    main()
