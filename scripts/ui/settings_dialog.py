import os
import logging
import time
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
                            QComboBox, QScrollArea, QPushButton, QGridLayout, QLineEdit, 
                            QWidget, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon

# Import pynput for keyboard capture
try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None
    logging.error("pynput library not found. Cannot capture keyboard shortcuts.")

from .theme import ThemeManager

class SettingsDialog(QDialog):
    """Dialog for application settings"""
    
    def __init__(self, parent=None, settings_manager=None, keyboard_service=None, audio_service=None, groq_service=None):
        super().__init__(parent)
        self.parent = parent
        self.settings_manager = settings_manager
        self.keyboard_service = keyboard_service
        self.audio_service = audio_service
        self.groq_service = groq_service
        self.shortcut_buttons = {}
        
        # Get the theme from settings
        self.theme = self.settings_manager.get('ui_theme', 'light')
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setStyleSheet(ThemeManager.get_dialog_style(self.theme))
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the settings dialog UI"""
        # Get theme colors
        colors = ThemeManager.get_theme(self.theme)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Create a scroll area to contain all settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Create a widget to contain all the settings
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        # UI Theme group
        theme_group = QGroupBox("UI Theme")
        theme_layout = QHBoxLayout()
        
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        
        # Set current theme
        current_theme_index = 1 if self.theme.lower() == "dark" else 0
        self.theme_combo.setCurrentIndex(current_theme_index)
        
        # Connect theme change signal
        self.theme_combo.currentIndexChanged.connect(self.theme_changed)
        theme_layout.addWidget(self.theme_combo)
        
        theme_group.setLayout(theme_layout)
        scroll_layout.addWidget(theme_group)
        
        # API Settings group
        api_group = QGroupBox("API Settings")
        api_layout = QGridLayout()
        api_layout.setColumnStretch(1, 1)  # Make the second column stretchable
        
        # API Key
        api_layout.addWidget(QLabel("Groq API Key:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your Groq API key")
        # Get saved API key from settings or fallback to config
        saved_api_key = self.settings_manager.get('groq_api_key', '')
        self.api_key_input.setText(saved_api_key)
        # Connect signal to save immediately
        self.api_key_input.textChanged.connect(self.save_api_key)
        api_layout.addWidget(self.api_key_input, 0, 1)
        
        # LLM Model
        api_layout.addWidget(QLabel("LLM Model:"), 1, 0)
        self.llm_model_combo = QComboBox()
        self.llm_model_combo.addItems([
            "llama-3.3-70b-versatile",
            "llama-3.1-8b",
            "llama-3.1-70b",
            "mixtral-8x7b",
            "gemma-7b"
        ])
        # Get saved model from settings or fallback to config
        saved_llm_model = self.settings_manager.get('llm_model', "llama-3.1-8b")
        # Find index of saved model
        model_index = self.llm_model_combo.findText(saved_llm_model)
        if model_index >= 0:
            self.llm_model_combo.setCurrentIndex(model_index)
        # Connect signal to save immediately
        self.llm_model_combo.currentTextChanged.connect(self.save_llm_model)
        api_layout.addWidget(self.llm_model_combo, 1, 1)
        
        # Transcription Model
        api_layout.addWidget(QLabel("Transcription Model:"), 2, 0)
        self.transcription_model_combo = QComboBox()
        self.transcription_model_combo.addItems([
            "whisper-large-v3",
            "whisper-medium",
            "whisper-small",
            "whisper-base"
        ])
        # Get saved model from settings or fallback to config
        saved_transcription_model = self.settings_manager.get('transcription_model', "whisper-large-v3")
        # Find index of saved model
        model_index = self.transcription_model_combo.findText(saved_transcription_model)
        if model_index >= 0:
            self.transcription_model_combo.setCurrentIndex(model_index)
        # Connect signal to save immediately
        self.transcription_model_combo.currentTextChanged.connect(self.save_transcription_model)
        api_layout.addWidget(self.transcription_model_combo, 2, 1)
        
        # Unfamiliar Words
        api_layout.addWidget(QLabel("Unfamiliar Words:"), 3, 0, Qt.AlignmentFlag.AlignTop)
        self.unfamiliar_words = QTextEdit()
        self.unfamiliar_words.setPlaceholderText("Enter unfamiliar words that might appear in transcriptions")
        self.unfamiliar_words.setMaximumHeight(100)  # Limit height
        # Get saved unfamiliar words from settings or fallback to config
        saved_unfamiliar_words = self.settings_manager.get('unfamiliar_words', "")
        self.unfamiliar_words.setText(saved_unfamiliar_words)
        # Connect signal to save immediately
        self.unfamiliar_words.textChanged.connect(self.save_unfamiliar_words)
        api_layout.addWidget(self.unfamiliar_words, 3, 1)
        
        api_group.setLayout(api_layout)
        scroll_layout.addWidget(api_group)
        
        # Microphone selection group
        mic_group = QGroupBox("Microphone")
        mic_layout = QHBoxLayout()
        mic_layout.addWidget(QLabel("Microphone:"))
        self.microphone_combo = QComboBox()
        
        # Add available microphones
        self.populate_microphones()
        
        # Set current microphone from settings
        saved_mic_index = self.settings_manager.get('microphone_index', 0)
        for i in range(self.microphone_combo.count()):
            if self.microphone_combo.itemData(i) == saved_mic_index:
                self.microphone_combo.setCurrentIndex(i)
                break
                
        # Connect signal to update immediately
        self.microphone_combo.currentIndexChanged.connect(self.microphone_changed)
        mic_layout.addWidget(self.microphone_combo)
        mic_group.setLayout(mic_layout)
        scroll_layout.addWidget(mic_group)
        
        # Keyboard shortcuts group
        shortcuts_group = QGroupBox("Keyboard Shortcuts")
        shortcuts_layout = QGridLayout()
        shortcuts_layout.setContentsMargins(10, 5, 10, 5)
        
        # Define shortcut actions and their display names
        shortcut_actions = [
            ('toggle_push_to_talk', "Push-to-talk toggle:"),
            ('toggle_recording', "Recording toggle:"),
            ('toggle_ai_processing', "AI processing toggle:"),
            ('toggle_auto_paste', "Auto-paste toggle:")
        ]
        
        # Create UI elements for each shortcut
        for row, (action_name, display_name) in enumerate(shortcut_actions):
            # Create label with transparent background
            label = QLabel(display_name)
            label.setStyleSheet(f"background: transparent; color: {colors['text_primary']};")
            shortcuts_layout.addWidget(label, row, 0)
            
            # Get the display string for the shortcut
            button_text = self.keyboard_service.get_shortcut_display_string(action_name)
            
            # Create button for this shortcut
            shortcut_btn = QPushButton(button_text)
            shortcut_btn.setToolTip("Click to set a new shortcut key (Escape/Delete to clear)")
            shortcut_btn.setMinimumWidth(120)
            
            # Set button style
            shortcut_btn.setStyleSheet(ThemeManager.get_inactive_button_style(self.theme))
            
            # Connect button to shortcut recording with the action name
            shortcut_btn.clicked.connect(lambda checked, action=action_name: self.start_shortcut_recording(action))
            
            # Add to layout
            shortcuts_layout.addWidget(shortcut_btn, row, 1)
            
            # Store reference to button for later updates
            self.shortcut_buttons[action_name] = shortcut_btn
        
        shortcuts_group.setLayout(shortcuts_layout)
        scroll_layout.addWidget(shortcuts_group)
        
        # Set the scroll content widget
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.setStyleSheet(ThemeManager.get_inactive_button_style(self.theme))
        self.close_button.clicked.connect(self.accept)
        
        # Add button to a centered layout
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.close_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)
    
    def theme_changed(self, index):
        """Handle theme change"""
        theme_name = "dark" if index == 1 else "light"
        
        # Save to settings
        self.settings_manager.set('ui_theme', theme_name)
        
        # Update dialog appearance
        self.theme = theme_name
        self.setStyleSheet(ThemeManager.get_dialog_style(theme_name))
        
        # Update button styles
        colors = ThemeManager.get_theme(theme_name)
        for btn in self.shortcut_buttons.values():
            btn.setStyleSheet(ThemeManager.get_inactive_button_style(theme_name))
            
        self.close_button.setStyleSheet(ThemeManager.get_inactive_button_style(theme_name))
        
        # Update all labels' color
        for label in self.findChildren(QLabel):
            label.setStyleSheet(f"background: transparent; color: {colors['text_primary']};")
        
        # If we have a parent, notify it to update its theme too
        if self.parent and hasattr(self.parent, 'change_theme'):
            self.parent.change_theme(theme_name)
    
    def save_api_key(self, text):
        """Save API key to settings"""
        self.settings_manager.set('groq_api_key', text)
        # If groq_service is available, update it directly
        if hasattr(self, 'groq_service') and self.groq_service:
            self.groq_service.api_key = text
    
    def save_llm_model(self, model_name):
        """Save LLM model to settings"""
        self.settings_manager.set('llm_model', model_name)
        # If groq_service is available, update it directly
        if hasattr(self, 'groq_service') and self.groq_service:
            self.groq_service.model = model_name
    
    def save_transcription_model(self, model_name):
        """Save transcription model to settings"""
        self.settings_manager.set('transcription_model', model_name)
        # If groq_service is available, update it directly
        if hasattr(self, 'groq_service') and self.groq_service:
            self.groq_service.transcription_model = model_name
    
    def save_unfamiliar_words(self):
        """Save unfamiliar words to settings"""
        text = self.unfamiliar_words.toPlainText()
        self.settings_manager.set('unfamiliar_words', text)
        # If groq_service is available, update it directly
        if hasattr(self, 'groq_service') and self.groq_service:
            self.groq_service.unfamiliar_words = text

    def log_error_message(self, message):
        """Log an error message to console"""
        logging.error(message)
        # If we have access to the main app's status bar, show it there too
        if hasattr(self, 'parent') and self.parent() and hasattr(self.parent(), 'statusBar'):
            try:
                self.parent().statusBar().showMessage(f"Error: {message}", 5000)
            except Exception:
                pass  # Ignore if we can't update the status bar
    
    def microphone_changed(self, index):
        """Handle microphone selection change"""
        if index >= 0:
            mic_index = self.microphone_combo.itemData(index)
            mic_name = self.microphone_combo.itemText(index)
            self.settings_manager.set('microphone_index', mic_index)
            self.settings_manager.set('microphone_name', mic_name)
    
    def populate_microphones(self):
        """Populate the microphone selection dropdown"""
        self.microphone_combo.clear()
        
        # Add all available microphones
        for device_id, device_name in self.audio_service.device_list:
            self.microphone_combo.addItem(f"{device_name}", device_id)
    
    def start_shortcut_recording(self, action_name):
        """Start recording a new keyboard shortcut for the given action using pynput"""
        if action_name not in self.shortcut_buttons:
            return
            
        button = self.shortcut_buttons[action_name]
        
        # Change button text to indicate recording state
        original_text = button.text()
        button.setText("Press any key...")
        button.setStyleSheet("QPushButton { background-color: #ffcccc; }")

        # Check if pynput is available
        if pynput_keyboard is None:
            logging.error("pynput library not found. Cannot capture keyboard shortcuts.")
            button.setText(original_text)
            button.setStyleSheet("")
            self.log_error_message("pynput library not found. Cannot capture keyboard shortcuts.")
            return

        # Temporarily stop keyboard service listener while capturing
        try:
            keyboard_service_active = False
            if hasattr(self.keyboard_service, '_pynput_listener') and self.keyboard_service._pynput_listener:
                self.keyboard_service.stop_listening()
                keyboard_service_active = True
                logging.debug("Temporarily stopped keyboard service listener for shortcut recording")
        except Exception as e:
            logging.error(f"Error stopping keyboard service listener: {e}")
        
        # Variables for capturing state
        is_captured = False
        captured_modifiers = set()
        captured_key = None
        captured_vk = None
        display_string = ""

        # Create a global variable to store key maps
        _CANCEL_KEYS = {pynput_keyboard.Key.esc, pynput_keyboard.Key.delete}
        
        # Callbacks for the temporary listener
        def on_press(key):
            nonlocal is_captured, captured_modifiers, captured_key, captured_vk, display_string
            
            if is_captured:
                return False  # Stop listener after capturing a key
            
            # Check for modifier keys
            modifier = None
            if key in (pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
                modifier = 'ctrl'
            elif key in (pynput_keyboard.Key.alt_l, pynput_keyboard.Key.alt_r, pynput_keyboard.Key.alt_gr):
                modifier = 'alt'
            elif key in (pynput_keyboard.Key.shift_l, pynput_keyboard.Key.shift_r):
                modifier = 'shift'
            elif key in (pynput_keyboard.Key.cmd_l, pynput_keyboard.Key.cmd_r, pynput_keyboard.Key.cmd):
                modifier = 'cmd'
                
            if modifier:
                captured_modifiers.add(modifier)
                return True  # Continue listening for the actual key
            
            # Check if it's a cancel key
            if key in _CANCEL_KEYS:
                # Clear the shortcut
                is_captured = True
                captured_key = None
                captured_vk = None
                display_string = "None"
                
                # Update on UI thread
                self.keyboard_service.set_shortcut_data(action_name, None)
                return False
            
            # Otherwise it's the main key of the shortcut
            is_captured = True
            captured_key = key
            
            # Try to get the virtual key code
            try:
                captured_vk = getattr(key, 'vk', None)
            except Exception:
                captured_vk = None
            
            # Create a display string
            parts = []
            if 'ctrl' in captured_modifiers:
                parts.append("Ctrl")
            if 'alt' in captured_modifiers:
                parts.append("Alt")
            if 'shift' in captured_modifiers:
                parts.append("Shift")
            if 'cmd' in captured_modifiers:
                parts.append("Win")
            
            try:
                # Try to get a display name for the key
                if hasattr(key, 'char') and key.char:
                    key_name = key.char.upper()
                elif hasattr(key, 'name') and key.name:
                    key_name = key.name.replace('_', ' ').title()
                else:
                    key_name = str(key).replace('Key.', '').upper()
                
                parts.append(key_name)
                display_string = '+'.join(parts)
            except Exception as e:
                logging.error(f"Error creating display string: {e}")
                display_string = '+'.join(parts) + "+" + str(key)
            
            # Stop the listener
            return False
        
        # Create a temporary listener
        listener = pynput_keyboard.Listener(on_press=on_press)
        listener.start()
        
        # Add a timeout to reset the button if no key is pressed
        def reset_button():
            if not is_captured and button.text() == "Press any key...":
                button.setText(original_text)
                button.setStyleSheet("")
                try:
                    listener.stop()
                except:
                    pass
                finally:
                    # Restart keyboard service listener
                    if keyboard_service_active:
                        self.keyboard_service.start_listening()
        
        # Schedule the reset after 5 seconds
        QTimer.singleShot(5000, reset_button)
        
        # Wait for the listener to finish (up to 5 seconds)
        listener.join(timeout=5.0)
        
        # Process the captured shortcut
        if is_captured:
            if captured_key:
                # Create shortcut data for KeyboardService
                shortcut_data = {
                    'mods': captured_modifiers,
                    'vk': captured_vk,
                    'key_repr': str(captured_key),
                    'display': display_string
                }
                
                # Update the shortcut in the service
                self.keyboard_service.set_shortcut_data(action_name, shortcut_data)
                
                # Update button display
                button.setText(display_string)
            else:
                # Clear the shortcut (cancel keys were pressed)
                button.setText("None")
            
            # Reset button style
            button.setStyleSheet("")
        
        # Restart keyboard service listener if it was active
        if keyboard_service_active:
            self.keyboard_service.start_listening()

    def get_selected_microphone(self):
        """Get the currently selected microphone index"""
        index = self.microphone_combo.currentIndex()
        if index >= 0:
            return self.microphone_combo.itemData(index)
        return None 