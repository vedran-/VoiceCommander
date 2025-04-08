SAVE_AUDIO_FILES = True
AUDIO_FILES_SAVE_FOLDER = "."     # TODO: Change where the audio files are saved

USE_LLM = True
VERBOSE_OUTPUT = False
CHAT_HISTORY_SAVE_FOLDER = "."    # TODO: Change where the chat history is saved
LLM_SANDBOX_WORKING_FOLDER = "."  # TODO: Change where the LLM sandbox files are saved

# These values serve as defaults and can be overridden in the settings UI
GROQ_API_KEY = ''  # Set through settings UI
LLM_MODEL = "llama-3.3-70b-versatile"  # Set through settings UI
TRANSCRIPTION_MODEL = "whisper-large-v3"  # Set through settings UI
MAX_TRANSCRIPTION_NO_SPEECH_PROBABILITY = 0.14

# Additional instructions for Transcription model (whisper)
UNFAMILIAR_WORDS = ("Some of the unfamilar words which might appear: "
                    "Mute, unmute, reset, copy, paste"
)

# Qt UI configuration
UI_THEME = "light"  # Options: "light", "dark"
UI_FONT_SIZE = 11
UI_SAVE_WINDOW_POSITION = True

# Language settings - comprehensive list of languages supported by whisper-large-v3
AVAILABLE_LANGUAGES = {
    'af': 'Afrikaans',
    'ar': 'Arabic',
    'hy': 'Armenian',
    'az': 'Azerbaijani',
    'be': 'Belarusian',
    'bs': 'Bosnian',
    'bg': 'Bulgarian',
    'ca': 'Catalan',
    'zh': 'Chinese',
    'hr': 'Croatian',
    'cs': 'Czech',
    'da': 'Danish',
    'nl': 'Dutch',
    'en': 'English',
    'et': 'Estonian',
    'fi': 'Finnish',
    'fr': 'French',
    'gl': 'Galician',
    'de': 'German',
    'el': 'Greek',
    'he': 'Hebrew',
    'hi': 'Hindi',
    'hu': 'Hungarian',
    'is': 'Icelandic',
    'id': 'Indonesian',
    'it': 'Italian',
    'ja': 'Japanese',
    'kn': 'Kannada',
    'kk': 'Kazakh',
    'ko': 'Korean',
    'lv': 'Latvian',
    'lt': 'Lithuanian',
    'mk': 'Macedonian',
    'ms': 'Malay',
    'mi': 'Maori',
    'mr': 'Marathi',
    'ne': 'Nepali',
    'no': 'Norwegian',
    'fa': 'Persian',
    'pl': 'Polish',
    'pt': 'Portuguese',
    'ro': 'Romanian',
    'ru': 'Russian',
    'sr': 'Serbian',
    'sk': 'Slovak',
    'sl': 'Slovenian',
    'es': 'Spanish',
    'sw': 'Swahili',
    'sv': 'Swedish',
    'tl': 'Tagalog',
    'ta': 'Tamil',
    'th': 'Thai',
    'tr': 'Turkish',
    'uk': 'Ukrainian',
    'ur': 'Urdu',
    'vi': 'Vietnamese',
    'cy': 'Welsh'
}
DEFAULT_LANGUAGE = 'en'

