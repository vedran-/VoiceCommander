import os
import json
import logging
import sys
import platform
from pathlib import Path

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
        'automatic_paste': True,
        'keyboard_shortcuts': {
            'toggle_push_to_talk': 'f8'  # Default shortcut for push-to-talk
        }
    }
    
    def __init__(self, settings_dir=None, settings_file='voice_commander_settings.json'):
        """
        Initialize the SettingsManager
        
        Args:
            settings_dir: Directory to store settings file (default: platform-specific user data directory)
            settings_file: Name of the settings file
        """
        if settings_dir is None:
            # Use platform-specific user data directory
            settings_dir = self._get_user_data_dir()
        
        self.settings_path = os.path.join(settings_dir, settings_file)
        
        # Try to migrate settings from old location if new location doesn't exist
        if not os.path.exists(self.settings_path):
            self._migrate_settings_from_old_location(settings_file)
        
        self.settings = self.load_settings()
        logger.info(f"Settings initialized from {self.settings_path}")
    
    def _get_user_data_dir(self):
        """
        Get platform-appropriate user data directory for storing settings
        
        Returns:
            Path to user data directory
        """
        # Use hidden folder for Windows and Linux
        app_name = "VoiceCommander"
        
        try:
            # Get platform-specific user data directory
            if platform.system() == "Windows":
                # Windows: AppData/Roaming
                if 'APPDATA' in os.environ:
                    base_dir = os.path.join(os.environ['APPDATA'], app_name)
                else:
                    # Fallback to user home directory if APPDATA is not available
                    base_dir = os.path.join(str(Path.home()), "." + app_name)
            elif platform.system() == "Darwin":
                # macOS: ~/Library/Application Support
                # Keep macOS convention (Library folder is already hidden by default)
                base_dir = os.path.join(str(Path.home()), "Library", "Application Support", app_name)
            else:
                # Linux/Unix: ~/.local/share
                base_dir = os.path.join(str(Path.home()), ".local", "share", app_name)
            
            # Create directory if it doesn't exist
            os.makedirs(base_dir, exist_ok=True)
            
            logger.info(f"Using settings directory: {base_dir}")
            return base_dir
            
        except Exception as e:
            # Fallback to user home directory if there's any issue
            # Use platform-specific fallback
            if platform.system() == "Darwin":
                # For macOS, use a hidden folder in home directory as fallback
                fallback_dir = os.path.join(str(Path.home()), f".{app_name}")
            else:
                fallback_dir = os.path.join(str(Path.home()), app_name)
                
            logger.error(f"Error determining user data directory: {e}. Using fallback: {fallback_dir}")
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir
    
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
    
    def _migrate_settings_from_old_location(self, settings_file):
        """
        Attempt to migrate settings from old location (script directory) to new location
        
        Args:
            settings_file: Name of the settings file
        """
        try:
            # Check if settings exist in the old location (script directory)
            old_dir = os.path.dirname(os.path.abspath(__file__))
            old_path = os.path.join(old_dir, settings_file)
            
            if os.path.exists(old_path):
                logger.info(f"Found settings in old location: {old_path}")
                
                # Read old settings
                with open(old_path, 'r') as f:
                    old_settings = json.load(f)
                
                # Save to new location
                os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
                with open(self.settings_path, 'w') as f:
                    json.dump(old_settings, f, indent=4)
                
                logger.info(f"Settings migrated from {old_path} to {self.settings_path}")
                
                # Optionally, create a backup of the old file
                backup_path = old_path + '.bak'
                try:
                    os.rename(old_path, backup_path)
                    logger.info(f"Created backup of old settings file at {backup_path}")
                except Exception as e:
                    logger.warning(f"Could not create backup of old settings file: {e}")
        
        except Exception as e:
            logger.warning(f"Failed to migrate settings from old location: {e}") 