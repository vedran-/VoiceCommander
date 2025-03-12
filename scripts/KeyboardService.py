import sys
import threading
import logging
import time
import traceback
import os
from . import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('KeyboardService')

# Import for window focus detection
try:
    import pygetwindow as gw
    has_window_focus_detection = True
    logger.info("Window focus detection enabled")
except ImportError:
    has_window_focus_detection = False
    logger.warning("Window focus detection not available - install pygetwindow package for better functionality")

# Use different import approach to avoid conflicts
keyboard_lib = None
global_keyboard = None

try:
    import keyboard as keyboard_lib
    logger.info("Successfully imported keyboard library for local shortcuts")
except ImportError as e:
    logger.error(f"Failed to import keyboard library for local shortcuts: {e}")
    print(f"Warning: Local keyboard shortcuts will not work. Error: {e}")

try:
    from pynput import keyboard as global_keyboard
    logger.info("Successfully imported pynput library for global shortcuts")
except ImportError as e:
    logger.error(f"Failed to import pynput library for global shortcuts: {e}")
    print(f"Warning: Global keyboard shortcuts will not work. Error: {e}")

class KeyboardService:
    def __init__(self, groq_service=None, transcription_service=None):
        """
        Initialize the KeyboardService
        
        Args:
            groq_service: The GroqWhisperService instance to control
            transcription_service: The TranscriptionService instance to control
        """
        logger.info("Initializing KeyboardService")
        self.groq_service = groq_service
        self.transcription_service = transcription_service
        self.local_listener = None
        self.global_listener = None
        self.command_handlers = {
            'mute_toggle': self._toggle_mute,
            'paste_toggle': self._toggle_paste,
            'reset': self._reset_chat,
            'language_en': lambda: self._switch_language('en'),
            'language_hr': lambda: self._switch_language('hr'),
            'language_sl': lambda: self._switch_language('sl'),
            'help': self._show_help,
            'transcription_toggle': self._toggle_transcription,
        }
        self.running = False
        self.last_key_time = 0
        self.key_cooldown = 0.3  # seconds
        self.ignore_next_keypress = False
        
        # Modifier key states
        self.ctrl_pressed = False
        self.alt_pressed = False
        self.shift_pressed = False
        
        # Key translation map for virtual key codes (useful for Windows)
        self.vk_to_char = {
            77: 'm',  # M key
            80: 'p',  # P key
            82: 'r',  # R key
            69: 'e',  # E key
            72: 'h',  # H key
            83: 's',  # S key
        }
        
        # Store application window title for focus detection
        self.app_window_title = self._get_app_window_title()
        logger.info(f"App window title for focus detection: {self.app_window_title}")
        
    def _get_app_window_title(self):
        """Get the title of the application window for focus detection"""
        # Try to determine a good window title to match against
        if hasattr(sys, 'executable'):
            # Get executable name without extension
            exe_name = os.path.basename(sys.executable)
            exe_name = os.path.splitext(exe_name)[0].lower()
            return exe_name
        return "python"  # Fallback
        
    def _is_app_in_focus(self):
        """Check if the application window is in focus"""
        if not has_window_focus_detection:
            return True  # If we can't detect focus, assume we're in focus for backward compatibility
            
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                # Match window titles that contain our app name, python, or powershell
                # that might be hosting our application
                title = active_window.title.lower()
                app_indicators = ["voice commander", "voicecommander", self.app_window_title, 
                                 "python", "powershell", "cmd", "command prompt"]
                                 
                for indicator in app_indicators:
                    if indicator in title:
                        logger.debug(f"App in focus - matched window title: {title}")
                        return True
                        
                if config.VERBOSE_OUTPUT:
                    logger.debug(f"App not in focus - active window: {title}")
                return False
        except Exception as e:
            logger.error(f"Error checking window focus: {e}")
            
        # Default to true if we can't determine focus
        return True
        
    def start(self):
        """Start keyboard shortcut listeners"""
        logger.info("Starting keyboard service")
        self.running = True
        
        local_setup_success = False
        global_setup_success = False
        
        # Setup local keyboard shortcuts
        if config.ENABLE_LOCAL_SHORTCUTS and keyboard_lib:
            try:
                logger.info("Setting up local keyboard shortcuts...")
                self._setup_local_shortcuts()
                local_setup_success = True
            except Exception as e:
                logger.error(f"Failed to setup local keyboard shortcuts: {e}")
                print(f"Warning: Failed to setup local keyboard shortcuts: {e}")
                traceback.print_exc()
        else:
            if not keyboard_lib:
                logger.warning("Local shortcuts disabled: keyboard library not available")
            else:
                logger.info("Local shortcuts disabled in config")
            
        # Setup global keyboard shortcuts
        if config.ENABLE_GLOBAL_SHORTCUTS and global_keyboard:
            try:
                logger.info("Setting up global keyboard shortcuts...")
                # Set up global keyboard in a non-blocking manner
                self.global_listener = global_keyboard.Listener(
                    on_press=self._on_global_key_press,
                    on_release=self._on_global_key_release
                )
                self.global_listener.daemon = True
                self.global_listener.start()
                if self.global_listener.is_alive():
                    logger.info(f"Global keyboard listener started successfully")
                    global_setup_success = True
                else:
                    logger.error(f"Global keyboard listener failed to start")
                    print(f"Warning: Global keyboard listener failed to start")
            except Exception as e:
                logger.error(f"Failed to setup global keyboard shortcuts: {e}")
                print(f"Warning: Failed to setup global keyboard shortcuts: {e}")
                traceback.print_exc()
        else:
            if not global_keyboard:
                logger.warning("Global shortcuts disabled: pynput library not available")
            else:
                logger.info("Global shortcuts disabled in config")
        
        if local_setup_success or global_setup_success:
            print("Keyboard shortcuts enabled.")
            self._show_help()
        else:
            print("WARNING: No keyboard shortcuts could be enabled. Voice commands only.")
        
    def _setup_local_shortcuts(self):
        """Setup local keyboard shortcuts"""
        try:
            for command, key in config.LOCAL_KEYBOARD_SHORTCUTS.items():
                if keyboard_lib:
                    def create_handler(cmd):
                        def handler():
                            try:
                                if not self.running:
                                    return
                                    
                                # Only process keypresses when the app is in focus
                                if not self._is_app_in_focus():
                                    logger.debug(f"Local command {cmd} ignored - app not in focus")
                                    return
                                    
                                # Cooldown check
                                current_time = time.time()
                                if current_time - self.last_key_time < self.key_cooldown:
                                    logger.debug(f"Command {cmd} ignored - cooldown active")
                                    return
                                self.last_key_time = current_time
                                    
                                logger.info(f"Local command detected: {cmd}")
                                
                                if cmd in self.command_handlers:
                                    logger.info(f"Executing local command: {cmd}")
                                    self.command_handlers[cmd]()
                                else:
                                    logger.warning(f"Local command not found: {cmd}")
                            except Exception as e:
                                logger.error(f"Error handling local command {cmd}: {e}")
                                
                        return handler
                        
                    keyboard_lib.add_hotkey(key, create_handler(command))
                    logger.info(f"Added local shortcut '{key}' for command '{command}'")
            
        except Exception as e:
            logger.error(f"Error while registering local keyboard shortcuts: {e}")
             
    def stop(self):
        """Stop keyboard shortcut listeners"""
        logger.info("Stopping keyboard service")
        self.running = False
        
        # Unregister local shortcuts
        if config.ENABLE_LOCAL_SHORTCUTS and keyboard_lib:
            try:
                keyboard_lib.unhook_all()
                logger.info("Unhooked all local shortcuts")
            except Exception as e:
                logger.error(f"Error unregistering local shortcuts: {e}")
                    
        # Stop global listener
        if config.ENABLE_GLOBAL_SHORTCUTS and self.global_listener:
            try:
                self.global_listener.stop()
                logger.info("Stopped global listener")
            except Exception as e:
                logger.error(f"Error stopping global listener: {e}")
    
    def _on_global_key_press(self, key):
        """
        Handle global key press events
        
        Args:
            key: The key that was pressed
        """
        if not self.running:
            return True  # Continue listening
        
        # Update modifier key states on key press
        try:
            if key == global_keyboard.Key.ctrl or key == global_keyboard.Key.ctrl_l or key == global_keyboard.Key.ctrl_r:
                self.ctrl_pressed = True
                logger.debug("CTRL pressed")
                return True
            elif key == global_keyboard.Key.alt or key == global_keyboard.Key.alt_l or key == global_keyboard.Key.alt_r:
                self.alt_pressed = True
                logger.debug("ALT pressed")
                return True
            elif key == global_keyboard.Key.shift or key == global_keyboard.Key.shift_l or key == global_keyboard.Key.shift_r:
                self.shift_pressed = True
                logger.debug("SHIFT pressed")
                return True
        except Exception as e:
            logger.error(f"Error processing modifier key: {e}")
            
        try:
            # Check if app is in focus for non-global shortcuts
            if not self._is_app_in_focus() and not (self.ctrl_pressed and self.alt_pressed):
                return True  # Ignore keypresses when app is not focused (except for ctrl+alt combos)
            
            # If we're supposed to ignore this keypress, just continue
            if self.ignore_next_keypress:
                logger.info(f"Ignoring programmatic keypress")
                self.ignore_next_keypress = False
                return True
                
            # Try to get key character using various methods
            key_char = self._get_key_char(key)
            
            # If we couldn't determine the key, just continue
            if key_char is None:
                return True
            
            # Debug output 
            if self.ctrl_pressed or self.alt_pressed or self.shift_pressed:
                logger.info(f"Modifiers: CTRL={self.ctrl_pressed}, ALT={self.alt_pressed}, SHIFT={self.shift_pressed}, Key={key_char}")
                
            # Check if any of the global shortcuts match
            matched = False
            for command, key_combo in config.GLOBAL_KEYBOARD_SHORTCUTS.items():
                key_parts = key_combo.lower().split('+')
                shortcut_ctrl = 'ctrl' in key_parts
                shortcut_alt = 'alt' in key_parts
                shortcut_shift = 'shift' in key_parts
                
                # Get the main key (last non-modifier part)
                main_key = None
                for part in key_parts:
                    if part not in ['ctrl', 'alt', 'shift']:
                        main_key = part
                
                # If modifiers match and the pressed key matches the main key of the shortcut
                if (main_key and
                    shortcut_ctrl == self.ctrl_pressed and 
                    shortcut_alt == self.alt_pressed and 
                    shortcut_shift == self.shift_pressed and 
                    (key_char == main_key or key_char.lower() == main_key)):
                    
                    logger.info(f"Global shortcut detected: {key_combo} for command {command}")
                    matched = True
                    
                    # Execute the command directly 
                    try:
                        if command in self.command_handlers:
                            logger.info(f"Executing global command: {command}")
                            self.command_handlers[command]()
                        else:
                            logger.warning(f"Global command not found: {command}")
                    except Exception as e:
                        logger.error(f"Error executing global command {command}: {e}")
                        
            # Return False to consume the event if we matched a shortcut
            if matched:
                return False
                
        except Exception as e:
            logger.error(f"Error handling global key press: {e}", exc_info=True)
            
        return True  # Always continue listening for non-matched keys
    
    def _get_key_char(self, key):
        """
        Get the character representation of a key
        
        Args:
            key: The key to get the character for
            
        Returns:
            The character representation of the key, or None if it couldn't be determined
        """
        key_char = None
        
        try:
            # Try to get character key
            if hasattr(key, 'char') and key.char is not None:
                key_char = key.char
                logger.debug(f"Character key: {key_char}")
                return key_char
            
            # Try to get named key
            if hasattr(key, 'name') and key.name is not None:
                key_char = key.name
                logger.debug(f"Named key: {key_char}")
                return key_char
            
            # Try to get key from Key enum
            key_str = str(key).lower()
            logger.debug(f"Raw key string: {key_str}")
            
            # Handle Key.* format
            if key_str.startswith('key.'):
                key_char = key_str.replace('key.', '')
                logger.debug(f"Key from enum: {key_char}")
                return key_char
                
            # Try to get virtual key code
            if hasattr(key, 'vk') and key.vk is not None:
                vk = key.vk
                
                # Check our translation map first
                if vk in self.vk_to_char:
                    key_char = self.vk_to_char[vk]
                    logger.debug(f"Key from VK map: {vk} -> {key_char}")
                    return key_char
                
                # Fall back to string representation
                key_char = str(vk).lower()
                logger.debug(f"Key from VK code: {key_char}")
                return key_char
                
            # Special cases for common keys
            if key == global_keyboard.Key.space:
                return 'space'
            elif key == global_keyboard.Key.enter:
                return 'enter'
            elif key == global_keyboard.Key.esc:
                return 'esc'
            elif key == global_keyboard.Key.tab:
                return 'tab'
                
        except Exception as e:
            logger.error(f"Error getting key character: {e}")
            
        if key_char is None:
            logger.warning(f"Could not determine key character for: {key}, type: {type(key)}")
            
        return key_char
    
    def _on_global_key_release(self, key):
        """
        Handle global key release events
        
        Args:
            key: The key that was released
        """
        if not self.running:
            return True  # Continue listening
            
        # Update modifier key states on key release
        try:
            if key == global_keyboard.Key.ctrl or key == global_keyboard.Key.ctrl_l or key == global_keyboard.Key.ctrl_r:
                self.ctrl_pressed = False
                logger.debug("CTRL released")
            elif key == global_keyboard.Key.alt or key == global_keyboard.Key.alt_l or key == global_keyboard.Key.alt_r:
                self.alt_pressed = False
                logger.debug("ALT released")
            elif key == global_keyboard.Key.shift or key == global_keyboard.Key.shift_l or key == global_keyboard.Key.shift_r:
                self.shift_pressed = False
                logger.debug("SHIFT released")
            else:
                # For debugging non-modifier keys
                key_str = str(key)
                logger.debug(f"Released key: {key_str}")
        except Exception as e:
            logger.error(f"Error processing key release: {e}")
            
        return True  # Always continue listening
    
    # Command handlers
    def _toggle_mute(self):
        """Toggle mute on/off"""
        if self.groq_service:
            was_muted = self.groq_service.mute_llm
            self.groq_service.mute_llm = not was_muted
            status = 'muted' if self.groq_service.mute_llm else 'unmuted'
            logger.info(f"AI chat {status}")
            print(f">>> AI chat {status}")
            
            # Only attempt TTS if we're unmuting or were not muted before
            if not was_muted or not self.groq_service.mute_llm:
                try:
                    # Play text-to-speech feedback
                    self.groq_service.safe_tts_say(f"AI {status}")
                except Exception as e:
                    logger.error(f"TTS error: {e}")
            
            # Set ignore flag to avoid handling keypress echoes
            self.ignore_next_keypress = True
            
    def _toggle_paste(self):
        """Toggle paste on/off"""
        if self.groq_service:
            was_muted = self.groq_service.mute_llm
            self.groq_service.automatic_paste = not self.groq_service.automatic_paste
            status = 'enabled' if self.groq_service.automatic_paste else 'disabled'
            logger.info(f"Automatic paste {status}")
            print(f">>> Automatic paste {status}")
            
            # Only attempt TTS if not muted
            if not was_muted:
                try:
                    # Play text-to-speech feedback
                    self.groq_service.safe_tts_say(f"Automatic paste {status}")
                except Exception as e:
                    logger.error(f"TTS error: {e}")
            
            # Set ignore flag
            self.ignore_next_keypress = True
    
    def _reset_chat(self):
        """Reset chat history"""
        if self.groq_service:
            was_muted = self.groq_service.mute_llm
            self.groq_service.InitializeChat()
            logger.info("Chat history reset")
            print(">>> Chat history reset")
            
            # Only attempt TTS if not muted
            if not was_muted:
                try:
                    self.groq_service.safe_tts_say("Chat history reset")
                except Exception as e:
                    logger.error(f"TTS error: {e}")
            
            # Set ignore flag
            self.ignore_next_keypress = True
    
    def _switch_language(self, lang_code):
        """
        Switch the language
        
        Args:
            lang_code: The language code (e.g. 'en', 'hr', 'sl')
        """
        if self.groq_service:
            was_muted = self.groq_service.mute_llm
            prev_lang = self.groq_service.language
            self.groq_service.language = lang_code.lower()
            
            # Map language codes to full names
            language_names = {
                'en': 'English',
                'hr': 'Croatian',
                'sl': 'Slovenian'
            }
            
            lang_name = language_names.get(lang_code.lower(), lang_code)
            logger.info(f"Language switched to {lang_name}")
            print(f">>> Language switched to {lang_name}")
            
            # Only attempt TTS if not muted
            if not was_muted:
                try:
                    self.groq_service.safe_tts_say(f"Language switched to {lang_name}")
                except Exception as e:
                    logger.error(f"TTS error: {e}")
            
            # Set ignore flag
            self.ignore_next_keypress = True
    
    def _show_help(self):
        """Show available commands"""
        print("\nAvailable keyboard shortcuts:")
        
        print("\nLocal shortcuts:")
        for command, key in config.LOCAL_KEYBOARD_SHORTCUTS.items():
            description = self._get_command_description(command)
            print(f"  {key} : {description}")
            
        print("\nGlobal shortcuts (work even when app doesn't have focus):")
        for command, key in config.GLOBAL_KEYBOARD_SHORTCUTS.items():
            description = self._get_command_description(command)
            print(f"  {key} : {description}")
        
        print("")
        logger.info("Help displayed")
        
        # Set ignore flag
        self.ignore_next_keypress = True
    
    def _get_command_description(self, command):
        """
        Get a human-readable description of a command
        
        Args:
            command: The command to describe
            
        Returns:
            The description of the command
        """
        descriptions = {
            'mute_toggle': "Toggle mute on/off",
            'paste_toggle': "Toggle paste on/off",
            'reset': "Reset chat history",
            'language_en': "Switch to English",
            'language_hr': "Switch to Croatian",
            'language_sl': "Switch to Slovenian",
            'help': "Show help/available commands",
        }
        
        return descriptions.get(command, command)
    
    def _toggle_transcription(self):
        """Toggle transcription on or off"""
        try:
            if not hasattr(self, 'transcription_enabled'):
                self.transcription_enabled = True
                
            self.transcription_enabled = not self.transcription_enabled
            
            if self.transcription_service:
                if self.transcription_enabled:
                    print("\033[92mTranscription RESUMED\033[0m")
                    try:
                        self.transcription_service.resume_transcription()
                    except Exception as e:
                        logger.error(f"Error resuming transcription: {e}")
                        print(f"\033[91mError resuming transcription: {e}\033[0m")
                        # Try to recover the enabled state
                        self.transcription_enabled = False
                else:
                    print("\033[91mTranscription STOPPED\033[0m")
                    try:
                        self.transcription_service.pause_transcription()
                    except Exception as e:
                        logger.error(f"Error pausing transcription: {e}")
                        print(f"\033[91mError pausing transcription: {e}\033[0m")
                        # Try to recover the enabled state
                        self.transcription_enabled = True
            else:
                if self.transcription_enabled:
                    print("\033[92mTranscription would be RESUMED (service not available)\033[0m")
                else:
                    print("\033[91mTranscription would be STOPPED (service not available)\033[0m") 
                    
            # Set ignore flag to avoid handling keypress echoes
            self.ignore_next_keypress = True
            
        except Exception as e:
            logger.error(f"Error toggling transcription: {e}")
            print(f"\033[91mError toggling transcription: {e}\033[0m") 