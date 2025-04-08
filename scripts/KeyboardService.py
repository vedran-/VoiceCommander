import logging
import sys
import platform
import threading
from PyQt6.QtCore import QObject, pyqtSignal

try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    # This case should ideally be handled before initializing the service,
    # but we include a fallback message.
    pynput_keyboard = None
    logging.getLogger('KeyboardService').error(
        "pynput library not found. KeyboardService will be disabled. "
        "Please install it: pip install pynput"
    )

logger = logging.getLogger('KeyboardService')

class KeyboardService(QObject):
    """
    Service for handling global keyboard shortcuts using pynput.Listener.
    Captures and compares modifier sets and key representations (VK code preferred).
    """
    # Signal emitted when a registered shortcut is triggered -> passes action_name
    shortcut_triggered = pyqtSignal(str)
    # Signal emitted if the listener fails to start
    keyboard_error = pyqtSignal(str)

    def __init__(self, settings_manager):
        """
        Initialize the KeyboardService.

        Args:
            settings_manager: SettingsManager instance to load/save shortcut settings.
        """
        super().__init__()
        self.settings_manager = settings_manager
        self.shortcuts = {}  # Stores {'action': {'mods': set(), 'vk': int|None, 'key_repr': str|None, 'display': str}}
        self.current_pressed_modifiers = set() # Tracks {'ctrl', 'alt', 'shift', 'cmd'}
        self._listener_thread = None
        self._listener_stop_event = threading.Event()
        self._pynput_listener = None # Holds the pynput listener instance

        if pynput_keyboard is None:
            self.keyboard_error.emit("pynput library not found. Shortcuts disabled.")
            logger.critical("pynput not found, KeyboardService disabled.")
            return # Do not proceed with initialization

        self._load_shortcuts()
        self.start_listening() # Start listener automatically

        logger.info("KeyboardService initialized using pynput.Listener.")
        logger.info(f"Loaded shortcuts: { {k: v.get('display', 'N/A') if v else 'None' for k, v in self.shortcuts.items()} }")


    def _load_shortcuts(self):
        """Load shortcuts from settings manager into the internal structure."""
        saved_data = self.settings_manager.get('keyboard_shortcuts', {})
        if not isinstance(saved_data, dict):
            logger.warning("Invalid keyboard shortcut data found in settings. Resetting.")
            saved_data = {}

        # Convert loaded data (mods might be list from JSON)
        self.shortcuts = {}
        for action, data in saved_data.items():
             # Check if data is the expected dictionary format
             if isinstance(data, dict) and 'mods' in data and ('vk' in data or 'key_repr' in data) and 'display' in data:
                 # Ensure mods is a set for efficient comparison
                 mods_set = set(data['mods'])
                 # Store the relevant parts
                 self.shortcuts[action] = {
                     'mods': mods_set,
                     'vk': data.get('vk'), # vk might be None
                     'key_repr': data.get('key_repr', str(data.get('vk'))), # Store representation if available
                     'display': data['display']
                 }
             elif data is None:
                 # Handle explicitly cleared shortcuts
                 self.shortcuts[action] = None
             else:
                 logger.warning(f"Skipping invalid shortcut data for action '{action}': {data}")
                 self.shortcuts[action] = None # Treat invalid data as unset

        # Ensure default actions exist, even if empty (set to None)
        default_actions = ['toggle_push_to_talk', 'toggle_recording', 'toggle_ai_processing', 'toggle_auto_paste']
        needs_save = False
        for action in default_actions:
            if action not in self.shortcuts:
                self.shortcuts[action] = None # Indicate no shortcut set
                needs_save = True

        # Save back if we added default keys or cleaned up invalid data
        if needs_save or not isinstance(saved_data, dict):
            self.settings_manager.set('keyboard_shortcuts', self._get_savable_shortcuts())


    def _get_savable_shortcuts(self):
        """Prepare the shortcuts dictionary for saving (convert sets to lists)."""
        savable = {}
        for action, data in self.shortcuts.items():
            # Save even if data is None (explicitly unset)
            if data:
                 savable[action] = {
                     'mods': sorted(list(data['mods'])), # Save mods as sorted list
                     'vk': data['vk'],
                     'key_repr': data.get('key_repr'), # Save key representation
                     'display': data['display']
                 }
            else:
                 savable[action] = None # Persist None for unset shortcuts
        return savable


    def start_listening(self):
        """Start the pynput listener in a separate thread."""
        if self._listener_thread is not None and self._listener_thread.is_alive():
            logger.warning("Listener thread already running.")
            return

        if pynput_keyboard is None:
            logger.error("Cannot start listener: pynput library not available.")
            self.keyboard_error.emit("pynput library not available.")
            return

        self._listener_stop_event.clear()
        # Use a non-daemon thread? If main app relies on signals, maybe daemon is ok.
        # Let's stick with daemon=True for now, assuming clean shutdown via stop_listening.
        self._listener_thread = threading.Thread(target=self._listener_run, daemon=True)
        self._listener_thread.start()
        logger.info("Keyboard listener thread started.")


    def stop_listening(self):
        """Stop the pynput listener thread."""
        if self._listener_thread and self._listener_thread.is_alive():
            logger.info("Stopping keyboard listener thread...")
            self._listener_stop_event.set()
            if self._pynput_listener:
                # pynput listener stop() can be called from any thread
                # It might raise exceptions if called multiple times or after join
                try:
                    self._pynput_listener.stop()
                except Exception as e:
                    logger.debug(f"Exception while stopping pynput listener (might be expected): {e}")
            # Don't join here - let the thread exit naturally after stop() is called.
            # Joining can block shutdown if the listener thread is stuck.
            # self._listener_thread.join(timeout=1.0)
            logger.info("Stop signal sent to listener thread.")
        self._listener_thread = None
        self._pynput_listener = None # Allow garbage collection


    def _listener_run(self):
        """Target method for the listener thread."""
        logger.info("pynput listener thread running...")
        try:
            # Context manager ensures stop() is called on exit/error
            with pynput_keyboard.Listener(
                    on_press=self._on_press,
                    on_release=self._on_release,
                    suppress=False # Set to True to block shortcuts system-wide
            ) as listener: # Store listener instance locally in the thread
                self._pynput_listener = listener # Share instance for external stop
                listener.join() # Blocks until listener.stop() is called

        except Exception as e:
            # Log error and emit signal for UI feedback
            error_msg = f"Failed to start pynput listener: {e}"
            logger.error(error_msg, exc_info=True)
            os_name = platform.system()
            if os_name == "Darwin": error_msg += " (Check Accessibility permissions?)"
            elif os_name == "Linux": error_msg += " (Wayland not supported? Run as root?)"
            elif os_name == "Windows": error_msg += " (Admin privileges needed? Conflicts?)"
            self.keyboard_error.emit(error_msg)
        finally:
            logger.info("pynput listener thread finished.")
            self._pynput_listener = None # Clear shared instance


    def _normalize_modifier(self, key):
         """Convert pynput modifier key object to simple string ('ctrl', 'alt', 'shift', 'cmd')."""
         if key in (pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r): return 'ctrl'
         if key in (pynput_keyboard.Key.alt_l, pynput_keyboard.Key.alt_r, pynput_keyboard.Key.alt_gr): return 'alt'
         if key in (pynput_keyboard.Key.shift_l, pynput_keyboard.Key.shift_r): return 'shift'
         # Treat cmd and windows key as 'cmd'
         if key in (pynput_keyboard.Key.cmd_l, pynput_keyboard.Key.cmd_r, pynput_keyboard.Key.cmd): return 'cmd'
         return None


    def _on_press(self, key):
        """Callback executed when a key is pressed."""
        # If stop event is set, ignore further presses
        if self._listener_stop_event.is_set():
            return False # Returning False should stop the listener

        normalized_mod = self._normalize_modifier(key)

        if normalized_mod:
            self.current_pressed_modifiers.add(normalized_mod)
            return # Don't check non-modifier logic

        # Non-modifier key pressed, check against registered shortcuts
        try:
            current_vk = getattr(key, 'vk', None)
        except Exception:
             current_vk = None

        for action_name, shortcut_data in self.shortcuts.items():
            if not shortcut_data: continue

            required_mods = shortcut_data['mods']
            target_vk = shortcut_data['vk']
            target_key_repr = shortcut_data.get('key_repr') # Use this for fallback/non-vk keys

            # 1. Check modifiers
            modifiers_match = (self.current_pressed_modifiers == required_mods)

            # 2. Check non-modifier key
            key_match = False
            if target_vk is not None and current_vk is not None and current_vk == target_vk:
                 key_match = True
            # Fallback: Check if VK is None for the target AND the string representations match
            # This helps with keys that don't have VK codes (like some media keys)
            elif target_vk is None and target_key_repr is not None and target_key_repr == str(key):
                 key_match = True

            # 3. Trigger if both match
            if modifiers_match and key_match:
                 logger.info(f"Shortcut MATCH: Action '{action_name}' triggered.")
                 try:
                     self.shortcut_triggered.emit(action_name)
                 except Exception as emit_err:
                      logger.error(f"Error emitting shortcut_triggered signal: {emit_err}")
                 # return False # Uncomment to block key from other apps ONLY if suppress=True
                 # Don't stop processing other actions for the same key press unless required

        # If stop event was set during processing, ensure listener stops
        return not self._listener_stop_event.is_set()


    def _on_release(self, key):
        """Callback executed when a key is released."""
        # If stop event is set, ignore further releases
        if self._listener_stop_event.is_set():
            return False

        normalized_mod = self._normalize_modifier(key)
        if normalized_mod:
            self.current_pressed_modifiers.discard(normalized_mod)

        # Check global stop event (for external stop calls)
        # No need for ESC check here, handle shutdown externally via stop_listening
        return not self._listener_stop_event.is_set()


    def set_shortcut_data(self, action_name, shortcut_data):
        """
        Updates the shortcut data for a specific action and saves settings.

        Args:
            action_name (str): The action identifier (e.g., 'toggle_recording').
            shortcut_data (dict | None): The dictionary containing {'mods': set, 'vk': int|None, 'key_repr': str|None, 'display': str}
                                          or None to clear the shortcut.
        """
        # Ensure action_name is valid if we maintain a strict list, otherwise just update
        # For now, assume action_name is valid as it comes from the UI
        # if action_name not in self.shortcuts: ...

        if shortcut_data:
            # Basic validation
            if not isinstance(shortcut_data, dict) or not all(k in shortcut_data for k in ['mods', 'vk', 'display', 'key_repr']):
                 logger.error(f"Invalid shortcut_data format for {action_name}: {shortcut_data}")
                 return False
            # Ensure mods is a set
            shortcut_data['mods'] = set(shortcut_data['mods'])
            self.shortcuts[action_name] = shortcut_data
            logger.info(f"Set shortcut for '{action_name}': {shortcut_data['display']}")
        else:
            # Clear shortcut
            self.shortcuts[action_name] = None
            logger.info(f"Cleared shortcut for '{action_name}'.")

        # Save updated shortcuts to settings file
        self.settings_manager.set('keyboard_shortcuts', self._get_savable_shortcuts())
        return True


    def get_shortcut_display_string(self, action_name):
        """
        Get the user-friendly display string for a shortcut action.

        Args:
            action_name (str): The action identifier.

        Returns:
            str: The display string (e.g., "Ctrl+Alt+H", "F8") or "None" if not set.
        """
        shortcut_data = self.shortcuts.get(action_name)
        if shortcut_data and shortcut_data.get('display'):
            return shortcut_data['display']
        return "None" # Default text if no shortcut is set or data is invalid

    def register_shortcut(self, action_name, callback_function):
        """
        Registers a callback function for a specific shortcut action.
        This maintains backward compatibility with the original KeyboardService.

        Args:
            action_name (str): The action identifier (e.g., 'toggle_recording').
            callback_function (function): The function to call when the shortcut is triggered.
        """
        logger.info(f"Registering callback for action: {action_name}")
        
        # Ensure the action exists in shortcuts dictionary
        if action_name not in self.shortcuts:
            self.shortcuts[action_name] = None
            
        # Connect the callback to the shortcut trigger signal for this action
        self.shortcut_triggered.connect(
            lambda action: callback_function() if action == action_name else None
        )
        
        return True
        
    def get_shortcut(self, action_name):
        """
        Backward compatibility method to get the shortcut string.
        
        Args:
            action_name (str): The action identifier.
            
        Returns:
            str: The display string or None if not set.
        """
        shortcut_data = self.shortcuts.get(action_name)
        if shortcut_data and shortcut_data.get('display'):
            return shortcut_data['display']
        return None
        
    def save_shortcuts(self):
        """
        Force saving the current shortcuts to the settings file.
        """
        self.settings_manager.set('keyboard_shortcuts', self._get_savable_shortcuts())
        logger.info("Keyboard shortcuts saved.")
        
    def get_friendly_key_name(self, key_str):
        """
        Backward compatibility method to convert key string to a friendly name.
        
        Args:
            key_str (str): The key string to convert.
            
        Returns:
            str: The friendly name for display.
        """
        # Now we just return the string as it should already be friendly
        return key_str 