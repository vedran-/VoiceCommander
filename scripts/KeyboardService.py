import logging
import threading
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger('KeyboardService')

class KeyboardService(QObject):
    """
    Service for handling global keyboard shortcuts
    """
    shortcut_triggered = pyqtSignal(str)  # Signal emitted when a registered shortcut is triggered
    
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
                'toggle_push_to_talk': 'f8'
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
    
    def _on_key_press(self, key):
        """
        Handle key press event from pynput
        
        Args:
            key: The key that was pressed
        """
        try:
            # Convert key to a standardized string representation
            key_str = self._normalize_key(key)
            
            # Add to currently pressed keys
            self.current_keys.add(key_str)
            
            # Check if any registered shortcut matches
            for action, shortcut in self.shortcuts.items():
                # For now, we only support single keys, not combinations
                if shortcut.lower() == key_str.lower():
                    logger.info(f"Shortcut triggered: {action} ({shortcut})")
                    
                    # Emit the signal with the action name
                    self.shortcut_triggered.emit(action)
                    
                    # Call the registered callback if any
                    if action in self.listeners:
                        self.listeners[action]()
        
        except Exception as e:
            logger.error(f"Error handling key press: {e}")
    
    def _on_key_release(self, key):
        """
        Handle key release event from pynput
        
        Args:
            key: The key that was released
        """
        try:
            # Convert key to a standardized string representation
            key_str = self._normalize_key(key)
            
            # Remove from currently pressed keys
            if key_str in self.current_keys:
                self.current_keys.remove(key_str)
        
        except Exception as e:
            logger.error(f"Error handling key release: {e}")
    
    def _normalize_key(self, key):
        """
        Convert a pynput key to a standardized string representation
        
        Args:
            key: pynput key object
        
        Returns:
            String representation of the key
        """
        # Special handling for different key types
        if hasattr(key, 'char') and key.char:
            # Alphanumeric keys
            return key.char.lower()
        elif hasattr(key, 'name') and key.name:
            # Special keys like F1, etc.
            return key.name.lower()
        elif hasattr(key, 'vk') and key.vk:
            # Handle media keys and others by virtual key code
            return f"vk{key.vk}"
        else:
            # Fallback
            return str(key).lower()
    
    def start_listening(self):
        """Start the keyboard listener"""
        try:
            # Create listener
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
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
        return self.start_listening()
    
    def stop_listening(self):
        """Stop the keyboard listener"""
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            logger.info("Keyboard listener stopped") 