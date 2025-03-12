SAVE_AUDIO_FILES = True
AUDIO_FILES_SAVE_FOLDER = "."     # TODO: Change where the audio files are saved

USE_LLM = True
VERBOSE_OUTPUT = False
CHAT_HISTORY_SAVE_FOLDER = "."    # TODO: Change where the chat history is saved
LLM_SANDBOX_WORKING_FOLDER = "."  # TODO: Change where the LLM sandbox files are saved

GROQ_API_KEY = '<your-groq-api-key>'  # TODO: Enter your Groq API key for Transcription and for LLM
LLM_MODEL = "llama-3.3-70b-versatile"
TRANSCRIPTION_MODEL = "whisper-large-v3"
MAX_TRANSCRIPTION_NO_SPEECH_PROBABILITY = 0.14

# Additional instructions for Transcription model (whisper)
UNFAMILIAR_WORDS = ("Some of the unfamilar words which might appear: "
                    "Mute, unmute, reset, copy, paste"
)


# Keyboard shortcut configuration
# Format: 'command': 'key'
# For global shortcuts, use GLOBAL_KEYBOARD_SHORTCUTS
# For local shortcuts, use LOCAL_KEYBOARD_SHORTCUTS
ENABLE_GLOBAL_SHORTCUTS = True
ENABLE_LOCAL_SHORTCUTS = True

LOCAL_KEYBOARD_SHORTCUTS = {
    'mute_toggle': 'm',        # Toggle mute on/off 
    'paste_toggle': 'p',       # Toggle paste on/off
    'reset': 'r',              # Reset chat history
    'language_en': 'alt+e',    # Switch to English
    'language_hr': 'alt+h',    # Switch to Croatian
    'language_sl': 'alt+s',    # Switch to Slovenian
    'help': 'h',               # Show help/available commands
    'transcription_toggle': 's', # Toggle transcription on/off
}

GLOBAL_KEYBOARD_SHORTCUTS = {
    'mute_toggle': 'ctrl+alt+m',   # Toggle mute on/off
    'paste_toggle': 'ctrl+alt+p',  # Toggle paste on/off
    'reset': 'ctrl+alt+r',         # Reset chat history
    'language_en': 'ctrl+alt+e',   # Switch to English
    'language_hr': 'ctrl+alt+h',   # Switch to Croatian
    'language_sl': 'ctrl+alt+s',   # Switch to Slovenian
    'help': 'ctrl+alt+shift+h',    # Show help/available commands
    'transcription_toggle': 'ctrl+alt+t', # Toggle transcription on/off
}

