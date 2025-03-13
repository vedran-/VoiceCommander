import os
import json
import logging

logger = logging.getLogger('SettingsManager')

class SettingsManager:
    """
    Manages application settings saving and loading
    """
    DEFAULT_SETTINGS = {
        'language': 'en',
        'microphone_index': 0,
        'microphone_name': '',
        'ui_theme': 'light',
        'window_position': None,
        'window_size': None,
        'mute_llm': True,
        'automatic_paste': True
    }
    
    def __init__(self, settings_dir=None, settings_file='voice_commander_settings.json'):
        """
        Initialize the SettingsManager
        
        Args:
            settings_dir: Directory to store settings file (default: app directory)
            settings_file: Name of the settings file
        """
        if settings_dir is None:
            # Use the directory of this file as the default
            settings_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.settings_path = os.path.join(settings_dir, settings_file)
        self.settings = self.load_settings()
        logger.info(f"Settings initialized from {self.settings_path}")
    
    def load_settings(self):
        """
        Load settings from file or use defaults if file doesn't exist
        
        Returns:
            Dictionary of settings
        """
        if not os.path.exists(self.settings_path):
            logger.info("Settings file not found, using defaults")
            return self.DEFAULT_SETTINGS.copy()
        
        try:
            with open(self.settings_path, 'r') as f:
                settings = json.load(f)
            
            # Make sure all default keys exist by updating with defaults 
            # for any missing keys
            default_copy = self.DEFAULT_SETTINGS.copy()
            default_copy.update(settings)
            return default_copy
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self):
        """
        Save current settings to file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
            
            logger.info("Settings saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def get(self, key, default=None):
        """
        Get a setting value
        
        Args:
            key: The setting key
            default: Default value if key doesn't exist
            
        Returns:
            The setting value or default
        """
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """
        Set a setting value
        
        Args:
            key: The setting key
            value: The value to set
            
        Returns:
            True if successful, False otherwise
        """
        self.settings[key] = value
        return self.save_settings()
    
    def update(self, settings_dict):
        """
        Update multiple settings at once
        
        Args:
            settings_dict: Dictionary of settings to update
            
        Returns:
            True if successful, False otherwise
        """
        self.settings.update(settings_dict)
        return self.save_settings() 