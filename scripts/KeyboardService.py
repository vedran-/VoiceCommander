import logging
import keyboard  # The keyboard library for global hotkey support
from PyQt6.QtCore import QObject, pyqtSignal
import sys

logger = logging.getLogger('KeyboardService')

class KeyboardService(QObject):
    """
    Simplified service for handling global keyboard shortcuts
    Supports complex shortcuts like 'ctrl+shift+a' and function keys
    """
    # Signal emitted when a shortcut is triggered
    shortcut_triggered = pyqtSignal(str)
    
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
        self.callback_refs = {}  # Keep strong references to callbacks to prevent garbage collection
        
        # Check if keyboard module has the required permissions
        if not self._check_keyboard_permissions():
            logger.error("Keyboard module may not have sufficient permissions to register global hotkeys")
            logger.error("On Windows, try running the application as Administrator")
            logger.error("On Linux, you might need to run as root or use sudo")
        
        # Load saved shortcuts from settings
        self._load_shortcuts()
        
        # Register all shortcuts
        self._register_all_shortcuts()
        
        # Debug information
        logger.info("KeyboardService initialized with keyboard library")
        logger.info(f"KeyboardService using shortcuts: {self.shortcuts}")
    
    def _check_keyboard_permissions(self):
        """Check if the keyboard module has necessary permissions to work"""
        try:
            # Try to perform a basic operation
            current_hooks = keyboard._listener.keyboards
            logger.info(f"Current keyboard hooks active: {len(current_hooks)}")
            return True
        except Exception as e:
            logger.error(f"Error accessing keyboard module: {e}")
            return False
    
    def _load_shortcuts(self):
        """Load shortcuts from settings"""
        # Get shortcuts from settings
        saved_shortcuts = self.settings_manager.get('keyboard_shortcuts', {})
        
        # Default shortcuts if none are set
        if not saved_shortcuts:
            saved_shortcuts = {
                'toggle_push_to_talk': 'f8',
                'toggle_recording': 'f7',
                'toggle_ai_processing': 'f9',
                'toggle_auto_paste': 'f10'
            }
            # Save defaults
            self.settings_manager.set('keyboard_shortcuts', saved_shortcuts)
        
        self.shortcuts = saved_shortcuts
        logger.info(f"Loaded keyboard shortcuts: {self.shortcuts}")
    
    def _register_all_shortcuts(self):
        """Register all shortcuts with the keyboard library"""
        try:
            # Clear all existing hotkeys first
            keyboard.unhook_all_hotkeys()
            logger.debug("Unhooked all existing keyboard hotkeys")
            
            # Register each shortcut
            for action_name, key_name in self.shortcuts.items():
                if key_name:
                    success = self._register_single_shortcut(action_name, key_name)
                    logger.info(f"Registered shortcut {action_name} -> {key_name}: {success}")
            
            # Debug: Log all active hooks
            self._log_active_hooks()
                    
        except Exception as e:
            logger.error(f"Error registering shortcuts: {e}")
    
    def _log_active_hooks(self):
        """Log active keyboard hooks for debugging"""
        try:
            if hasattr(keyboard, '_hotkeys'):
                hotkeys = keyboard._hotkeys
                logger.info(f"Active hotkeys: {len(hotkeys)}")
                for hotkey in hotkeys:
                    logger.info(f"  Hotkey: {hotkey}")
            if hasattr(keyboard, '_listener') and hasattr(keyboard._listener, 'handlers'):
                handlers = keyboard._listener.handlers
                logger.info(f"Keyboard handlers: {len(handlers)}")
        except Exception as e:
            logger.error(f"Error logging active hooks: {e}")
    
    def _register_single_shortcut(self, action_name, key_name):
        """Register a single shortcut with the keyboard library"""
        try:
            # Create a unique wrapper callback that will not be garbage collected
            def shortcut_callback_wrapper():
                logger.info(f"HOTKEY TRIGGERED: {action_name} ({key_name})")
                
                # Emit the signal - this will be received by any connected slots
                self.shortcut_triggered.emit(action_name)
                
                # Call the registered callback for this action if any
                if action_name in self.listeners:
                    try:
                        logger.info(f"Calling listener for {action_name}")
                        self.listeners[action_name]()
                    except Exception as e:
                        logger.error(f"Error in shortcut callback for {action_name}: {e}")
            
            # Store a strong reference to the callback to prevent garbage collection
            self.callback_refs[action_name] = shortcut_callback_wrapper
            
            # Try to directly use the keyboard hook for testing
            keyboard.on_press_key(key_name, lambda _: logger.info(f"Direct key press detected: {key_name}"))
            
            # Register the hotkey - use suppress=True to ensure it's captured
            try:
                keyboard.add_hotkey(key_name, shortcut_callback_wrapper, suppress=False)
                logger.info(f"Successfully registered hotkey for {action_name} -> {key_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to add_hotkey {key_name}: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to register shortcut {action_name} -> {key_name}: {e}")
            return False
    
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
            
            # Re-register the shortcut to ensure it uses the new callback
            key_name = self.shortcuts[action_name]
            if key_name:
                self._register_single_shortcut(action_name, key_name)
                
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
        # Update shortcut dictionary
        if key_name is None:
            # Clear the shortcut
            if action_name in self.shortcuts:
                self.shortcuts.pop(action_name)
                logger.info(f"Cleared shortcut for {action_name}")
        else:
            # Set the new shortcut
            self.shortcuts[action_name] = key_name
            logger.info(f"Set shortcut for {action_name} to {key_name}")
        
        # Save to settings
        self.settings_manager.set('keyboard_shortcuts', self.shortcuts)
        
        # Re-register all shortcuts with the new configuration
        self._register_all_shortcuts()
        
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
        """Start listening for keyboard shortcuts"""
        self._register_all_shortcuts()
        return True
    
    def restart_listener(self):
        """Restart the keyboard shortcut listener"""
        self._register_all_shortcuts()
        return True
    
    def stop_listening(self):
        """Stop listening for keyboard shortcuts"""
        try:
            keyboard.unhook_all_hotkeys()
            logger.info("Keyboard shortcuts unregistered")
        except Exception as e:
            logger.error(f"Error stopping keyboard listener: {e}")
    
    def is_cancel_key(self, key_str):
        """
        Check if the key should be interpreted as a cancel action
        
        Args:
            key_str: Key string
            
        Returns:
            True if this is a cancel key, False otherwise
        """
        return key_str.lower() in self.CANCEL_KEYS
    
    def _normalize_key(self, key):
        """
        Convert a key object to a standardized string representation
        
        Args:
            key: A key object (could be from pynput, keyboard lib, or a string)
            
        Returns:
            String representation of the key
        """
        try:
            # Handle keyboard library key objects
            if hasattr(key, 'name'):
                return key.name.lower()
            elif hasattr(key, 'char'):
                return key.char.lower()
            elif isinstance(key, str):
                return key.lower()
            else:
                # Fallback
                key_str = str(key).lower()
                # Remove 'key.' prefix if it exists (common in key libraries)
                if key_str.startswith('key.'):
                    return key_str[4:]
                return key_str
        except Exception as e:
            logger.error(f"Error normalizing key: {e}")
            return str(key).lower()
    
    def get_friendly_key_name(self, key_code):
        """
        Get a friendly display name for a key code
        
        Args:
            key_code: Key code as a string (e.g., 'f8', 'ctrl+s')
            
        Returns:
            Friendly display name for the key
        """
        if not key_code:
            return "None"
            
        # The keyboard library already uses friendly names, just return as is
        # For complex shortcuts like 'ctrl+shift+a', this will return as-is
        return key_code 