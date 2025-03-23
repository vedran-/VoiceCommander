import logging
import threading
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal
import time

logger = logging.getLogger('KeyboardService')

class KeyboardService(QObject):
    """
    Service for handling global keyboard shortcuts
    """
    shortcut_triggered = pyqtSignal(str)  # Signal emitted when a registered shortcut is triggered
    
    # Mapping of virtual key codes to friendly names for special keys
    KEY_MAPPINGS = {
        # Windows multimedia keys
        173: "Mute",
        174: "Volume Down",
        175: "Volume Up",
        176: "Next Track",
        177: "Previous Track",
        178: "Stop",
        179: "Play/Pause",
        180: "Mail",
        181: "Media",
        182: "App 1",
        183: "App 2",
        # Windows browser keys
        166: "Browser Back",
        167: "Browser Forward",
        168: "Browser Refresh",
        169: "Browser Stop",
        170: "Browser Search",
        171: "Browser Favorites",
        172: "Browser Home",
        # Windows system keys
        91: "Windows",
        92: "Windows Right",
        93: "Menu",
        # Calculator and other app keys
        148: "My Computer", 
        183: "Calculator",
        # Media keys - may overlap with others depending on keyboard
        407: "Media Play",
        408: "Media Stop",
        401: "Browser Home"
    }
    
    # Keys that should be interpreted as "cancel" when setting shortcuts
    CANCEL_KEYS = ['esc', 'delete', 'backspace']
    
    def __init__(self, settings_manager):
        """
        Initialize the KeyboardService
        
        Args:
            settings_manager: SettingsManager instance to load/save shortcut settings
        """
        super().__init__()
        self.settings_manager = settings_manager
        self.shortcuts = {}  # Dictionary mapping action_name -> key combination
        self.listeners = {}  # Dictionary mapping action_name -> callback function
        self.keyboard_listener = None
        self.current_keys = set()  # Currently pressed keys
        self.consume_keys = True   # Whether to consume key presses
        self.suppressed_keys = set()  # Keys that are currently suppressed
        
        # Create keyboard controller for re-injecting non-shortcut keys
        self.keyboard_controller = keyboard.Controller()
        
        # Load saved shortcuts from settings
        self._load_shortcuts()
        
        # Start keyboard listener in a separate thread
        self.start_listening()
    
    def _load_shortcuts(self):
        """Load shortcuts from settings"""
        # Get shortcuts dictionary from settings, use empty dict as default
        saved_shortcuts = self.settings_manager.get('keyboard_shortcuts', {})
        
        # Default shortcuts if none are set
        if not saved_shortcuts:
            # Set default for toggle_push_to_talk to F8
            saved_shortcuts = {
                'toggle_push_to_talk': 'f8',
                'toggle_recording': 'f7',
                'toggle_ai_processing': 'f9',
                'toggle_auto_paste': 'f10'
            }
            # Save the defaults
            self.settings_manager.set('keyboard_shortcuts', saved_shortcuts)
        
        self.shortcuts = saved_shortcuts
        logger.info(f"Loaded keyboard shortcuts: {self.shortcuts}")
    
    def register_shortcut(self, action_name, callback):
        """
        Register a callback for a shortcut action
        
        Args:
            action_name: Name of the action (must match a key in shortcuts dict)
            callback: Function to call when the shortcut is triggered
        
        Returns:
            True if registered successfully, False otherwise
        """
        if action_name in self.shortcuts:
            self.listeners[action_name] = callback
            logger.info(f"Registered callback for shortcut action: {action_name}")
            return True
        else:
            logger.warning(f"Cannot register callback for unknown action: {action_name}")
            return False
    
    def set_shortcut(self, action_name, key_name):
        """
        Set a shortcut for an action
        
        Args:
            action_name: Name of the action
            key_name: Name of the key (e.g., 'f8', 'ctrl+s')
            
        Returns:
            True if set successfully, False otherwise
        """
        # Handle the case of clearing a shortcut
        if key_name is None:
            if action_name in self.shortcuts:
                self.shortcuts.pop(action_name)
                logger.info(f"Cleared shortcut for {action_name}")
            
            # Save to settings
            self.settings_manager.set('keyboard_shortcuts', self.shortcuts)
            return True
            
        # Update the shortcuts dictionary
        self.shortcuts[action_name] = key_name
        
        # Save to settings
        self.settings_manager.set('keyboard_shortcuts', self.shortcuts)
        logger.info(f"Set shortcut for {action_name} to {key_name}")
        
        # Restart the listener to apply the new shortcuts
        self.restart_listener()
        
        return True
    
    def get_shortcut(self, action_name):
        """
        Get the current shortcut for an action
        
        Args:
            action_name: Name of the action
        
        Returns:
            Key name for the shortcut, or None if no shortcut is set
        """
        return self.shortcuts.get(action_name)
    
    def start_listening(self):
        """Start the keyboard listener"""
        try:
            # Create listener with selective key suppression
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
                suppress=False  # Only suppress keys in the callback handlers
            )
            
            # Start the listener in a daemon thread
            self.keyboard_listener.daemon = True
            self.keyboard_listener.start()
            
            logger.info("Keyboard listener started")
            return True
        
        except Exception as e:
            logger.error(f"Error starting keyboard listener: {e}")
            return False
    
    def restart_listener(self):
        """Restart the keyboard listener"""
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        # Clear suppressed keys when restarting
        self.suppressed_keys.clear()
        return self.start_listening()
    
    def stop_listening(self):
        """Stop the keyboard listener"""
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            logger.info("Keyboard listener stopped")
    
    def is_cancel_key(self, key_str):
        """
        Check if the key should be interpreted as a cancel action
        
        Args:
            key_str: Normalized key string
            
        Returns:
            True if this is a cancel key, False otherwise
        """
        return key_str.lower() in self.CANCEL_KEYS 
    
    def _schedule_listener_restart(self):
        """Schedule a restart of the keyboard listener to ensure it keeps working"""
        def delayed_restart():
            logger.info("Performing scheduled listener restart")
            # Wait a moment to ensure current key processing is complete
            time.sleep(0.1)
            self.restart_listener()
            
        # Start the restart in a background thread
        restart_thread = threading.Thread(target=delayed_restart)
        restart_thread.daemon = True
        restart_thread.start() 

    def _is_shortcut_key(self, key_str):
        """
        Check if a key string matches any of our registered shortcuts
        
        Args:
            key_str: Normalized key string
            
        Returns:
            (action_name, shortcut) tuple if matched, otherwise (None, None)
        """
        # Check each shortcut for a match
        for action, shortcut in self.shortcuts.items():
            if shortcut and shortcut.lower() == key_str.lower():
                return action, shortcut
        return None, None 
    
    def _on_key_press(self, key):
        """
        Handle key press event from pynput
        
        Args:
            key: The key that was pressed
            
        Returns:
            False to suppress the key press if it's a shortcut, True otherwise
        """
        try:
            # Convert key to a standardized string representation
            key_str = self._normalize_key(key)
            
            # Add to currently pressed keys
            self.current_keys.add(key_str)
            
            # Check if this is one of our shortcuts
            action_name, shortcut = self._is_shortcut_key(key_str)
            
            if action_name:
                # This is a shortcut key - process it
                logger.info(f"Shortcut triggered: {action_name} ({shortcut})")
                
                # Remember that we're suppressing this key
                if self.consume_keys:
                    self.suppressed_keys.add(key_str)
                
                # Emit the signal with the action name
                self.shortcut_triggered.emit(action_name)
                
                # Call the registered callback if any
                if action_name in self.listeners:
                    self.listeners[action_name]()
                
                # Schedule a restart of the listener to ensure future shortcuts work
                self._schedule_listener_restart()
                
                # Return False to suppress the key press only if it's a shortcut
                if self.consume_keys:
                    return False
        
        except Exception as e:
            logger.error(f"Error handling key press: {e}")
        
        # Allow all other keys to propagate to other applications
        return True
    
    def _on_key_release(self, key):
        """
        Handle key release event from pynput
        
        Args:
            key: The key that was released
            
        Returns:
            False to suppress the key release if it's a shortcut key,
            True to allow the key release to be processed by other applications
        """
        try:
            # Convert key to a standardized string representation
            key_str = self._normalize_key(key)
            
            # Check if this key was suppressed during press
            is_suppressed = key_str in self.suppressed_keys
            
            # Remove from currently pressed and suppressed keys
            if key_str in self.current_keys:
                self.current_keys.remove(key_str)
            
            if key_str in self.suppressed_keys:
                self.suppressed_keys.remove(key_str)
            
            # Return False to suppress the key release for shortcut keys
            if is_suppressed and self.consume_keys:
                return False
        
        except Exception as e:
            logger.error(f"Error handling key release: {e}")
        
        # Allow all other key releases to propagate
        return True
    
    def _normalize_key(self, key):
        """
        Convert a pynput key to a standardized string representation
        
        Args:
            key: pynput key object
        
        Returns:
            String representation of the key
        """
        # Special handling for different key types
        try:
            # First check virtual key codes for special keys
            if hasattr(key, 'vk') and key.vk:
                # Check if we have a friendly name for this virtual key code
                if key.vk in self.KEY_MAPPINGS:
                    return self.KEY_MAPPINGS[key.vk]
                
                # Handle media keys and others by virtual key code
                return f"Key_0x{key.vk:02x}"
            # Then check named keys (like F1, etc.)
            elif hasattr(key, 'name') and key.name:
                # Special keys like F1, etc.
                return key.name.lower()
            # Finally check character keys
            elif hasattr(key, 'char') and key.char:
                # Alphanumeric keys
                return key.char.lower()
            else:
                # Fallback
                return str(key).lower()
        except Exception as e:
            logger.error(f"Error normalizing key: {e}")
            # Fallback to string representation
            return str(key).lower()
    
    def get_friendly_key_name(self, key_code):
        """
        Get a friendly display name for a key code
        
        Args:
            key_code: Key code as a string (e.g., 'f8', 'vk173')
            
        Returns:
            Friendly display name for the key
        """
        # Check if it's a virtual key code
        if key_code.startswith("vk") or key_code.startswith("Key_0x"):
            try:
                # Extract the numeric part
                if key_code.startswith("vk"):
                    vk = int(key_code[2:], 10)
                else:  # Key_0x format
                    vk = int(key_code[6:], 16)
                
                # Look up in our mapping
                if vk in self.KEY_MAPPINGS:
                    return self.KEY_MAPPINGS[vk]
            except ValueError:
                pass
        
        # Just return the original if we don't have a mapping
        return key_code 