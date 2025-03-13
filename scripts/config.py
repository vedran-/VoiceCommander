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

# Qt UI configuration
UI_THEME = "light"  # Options: "light", "dark"
UI_FONT_SIZE = 11
UI_SAVE_WINDOW_POSITION = True

# Language settings
AVAILABLE_LANGUAGES = {
    'en': 'English',
    'hr': 'Croatian',
    'sl': 'Slovenian'
}
DEFAULT_LANGUAGE = 'en'

