Listens to your microphone and transcribes the audio into text, and the copies the text to the clipboard.


### Installation
```
pip install .
```

### Configuration
Before using Voice Commander, you need to configure your settings in the `config.py` file:

1. **Required**: Set your Groq API key
   ```python
   GROQ_API_KEY = 'your-groq-api-key'  # Required for transcription and LLM features
   ```

2. **Optional**: Configure folder locations for saved files
   ```python
   AUDIO_FILES_SAVE_FOLDER = "/path/to/save/audio/files"
   CHAT_HISTORY_SAVE_FOLDER = "/path/to/save/chat/history"
   LLM_SANDBOX_WORKING_FOLDER = "/path/to/llm/sandbox"
   ```

3. **Optional**: Adjust other settings like keyboard shortcuts in the same file

### Running

```bash
vc [--llm] [-d DEVICE_INDEX]
```

Where:
- `--llm`: Enable LLM processing
- `-d DEVICE_INDEX` or `--device DEVICE_INDEX`: Specify the audio input device index to use (skip the device selection prompt)

### Keyboard Shortcuts

Voice Commander now supports both application-local and global keyboard shortcuts for quick access to commands.

#### Local Shortcuts (active when application is in focus)
- `m` - Toggle AI chat mute on/off
- `p` - Toggle automatic paste on/off
- `r` - Reset chat history
- `alt+e` - Switch to English
- `alt+h` - Switch to Croatian
- `alt+s` - Switch to Slovenian
- `h` - Show help and available commands

#### Global Shortcuts (active system-wide)
- `ctrl+alt+m` - Toggle AI chat mute on/off
- `ctrl+alt+p` - Toggle automatic paste on/off
- `ctrl+alt+r` - Reset chat history
- `ctrl+alt+e` - Switch to English
- `ctrl+alt+h` - Switch to Croatian
- `ctrl+alt+s` - Switch to Slovenian
- `ctrl+alt+shift+h` - Show help and available commands

Shortcuts can be configured in the `config.py` file.

## Recent Fixes

### Keyboard Shortcut Fixes (March 10, 2025)

We resolved issues with keyboard shortcuts in this update:

1. **Local Keyboard Shortcuts**: Fixed an issue where the program only responded to the first keypress and then stopped responding.
   - Added `suppress=True` parameter to keyboard hotkey registration
   - Fixed an issue where the ignore_next_keypress flag was being reset incorrectly
   - Reduced lock timeout to avoid deadlocks

2. **Global Keyboard Shortcuts**: Fixed issues with global hotkeys not responding.
   - Improved key character recognition and detection
   - Added proper event consumption (return False) to handle global shortcuts
   - Added better debug logging to trace shortcut detection

3. **General Improvements**:
   - Added comprehensive logging throughout the keyboard service
   - Improved error handling for keyboard library dependencies
   - Fixed thread lock issues with shorter timeouts

To enable DEBUG level logging for more verbose information, add this to the main.py file:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
