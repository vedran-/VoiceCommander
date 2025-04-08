import sys
import os
import logging
import time
import json
import random
import importlib
import platform
import keyboard  # Import the keyboard library we're using
import pyperclip  # For clipboard operations
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtWidgets import QTextEdit, QLabel, QComboBox, QSplitter, QGroupBox, QGridLayout, QScrollArea
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QDialog, QDialogButtonBox, QLineEdit  # Added QLineEdit
from PyQt6.QtWidgets import QSizePolicy # <<< ADDED IMPORT
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QMetaObject, QTimer, QPoint, QSettings, QSize
from PyQt6.QtGui import QColor, QTextCursor, QFont, QIcon, QPalette, QAction, QPixmap, QCloseEvent, QPainter, QBrush
from functools import partial  # Added for creating button callbacks
import wave  # Added for reading WAV files
import pygame  # Added for playing audio

# Import pynput for keyboard capture
try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None
    logging.error("pynput library not found. Cannot capture keyboard shortcuts.")

# Import our services
from . import dependencies
from . import VoskService
from . import AudioService
from . import TranscriptionService
from . import SettingsManager
from . import KeyboardService
from . import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('VoiceCommander')

# Print application version information
print("Voice Commander Qt v0.3.0\n")
print("Starting the Qt-based Voice Commander application...")

class ThemeManager:
    """Manages application themes and provides styling"""
    
    # Light theme colors
    LIGHT_THEME = {
        "bg_primary": "#f8f9fc",
        "bg_secondary": "#ffffff",
        "bg_accent": "#eef1fa",
        "text_primary": "#505a7a",
        "text_secondary": "#8892b0",
        "border": "#e1e5ee",
        "accent": "#5b87f7",
        "accent_hover": "#4a76e6",
        "accent_pressed": "#3a65d5",
        "success": "#10b981",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "inactive": "#f1f3fa",
        "inactive_hover": "#e1e5ee",
        "inactive_pressed": "#d1d6e6",
        "scrollbar": "#f1f3fa",
        "scrollbar_handle": "#cbd2e6",
        "scrollbar_handle_hover": "#a8b3d2"
    }
    
    # Dark theme colors - modern, sleek dark theme
    DARK_THEME = {
        "bg_primary": "#16161a",
        "bg_secondary": "#242629",
        "bg_accent": "#2e2f35",
        "text_primary": "#fffffe",
        "text_secondary": "#94a1b2",
        "border": "#383a41",
        "accent": "#7f5af0",
        "accent_hover": "#6b47d9",
        "accent_pressed": "#5a3ec4",
        "success": "#2cb67d",
        "warning": "#ff8906",
        "error": "#f25042",
        "inactive": "#2c2c34",
        "inactive_hover": "#3e3e48",
        "inactive_pressed": "#494952",
        "scrollbar": "#242629",
        "scrollbar_handle": "#383a41",
        "scrollbar_handle_hover": "#4d4d57"
    }
    
    @classmethod
    def get_theme(cls, theme_name="light"):
        """Get theme colors dictionary"""
        return cls.DARK_THEME if theme_name.lower() == "dark" else cls.LIGHT_THEME
    
    @classmethod
    def get_main_window_style(cls, theme):
        """Get stylesheet for main window"""
        colors = cls.get_theme(theme)
        return f"""
            QMainWindow {{
                background-color: {colors["bg_primary"]};
            }}
            QWidget {{
                font-family: 'Segoe UI', sans-serif;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {colors["border"]};
                border-radius: 8px;
                margin-top: 12px;
                background-color: {colors["bg_secondary"]};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {colors["text_primary"]};
            }}
            QLabel {{
                color: {colors["text_primary"]};
            }}
            QComboBox {{
                border: 1px solid {colors["border"]};
                border-radius: 6px;
                padding: 5px;
                background-color: {colors["bg_secondary"]};
                color: {colors["text_primary"]};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {colors["bg_secondary"]};
                border: 1px solid {colors["border"]};
                border-radius: 6px;
                selection-background-color: {colors["bg_accent"]};
                selection-color: {colors["text_primary"]};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {colors["scrollbar"]};
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {colors["scrollbar_handle"]};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {colors["scrollbar_handle_hover"]};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: {colors["scrollbar"]};
                height: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {colors["scrollbar_handle"]};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {colors["scrollbar_handle_hover"]};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}
            QSplitter::handle {{
                background-color: {colors["border"]};
                height: 1px;
            }}
            QListWidget {{
                border: 1px solid {colors["border"]};
                border-radius: 8px;
                background-color: {colors["bg_secondary"]};
                alternate-background-color: {colors["bg_primary"]};
            }}
            QListWidget::item {{
                border-bottom: 1px solid {colors["border"]};
                padding: 3px;
            }}
            QListWidget::item:selected {{
                background-color: {colors["bg_accent"]};
                color: {colors["text_primary"]};
            }}
            QTextEdit {{
                border: 1px solid {colors["border"]};
                border-radius: 8px;
                background-color: {colors["bg_secondary"]};
                selection-background-color: {colors["accent"]};
                selection-color: #ffffff;
                color: {colors["text_primary"]};
            }}
        """
    
    @classmethod
    def get_active_button_style(cls, theme):
        """Get active button style"""
        colors = cls.get_theme(theme)
        return f"""
            QPushButton {{
                min-width: 110px;
                min-height: 36px;
                max-height: 36px;
                padding: 8px;
                border-radius: 6px;
                border: none;
                background-color: {colors["accent"]};
                color: white;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {colors["accent_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {colors["accent_pressed"]};
                min-height: 36px;
                max-height: 36px;
            }}
            QPushButton:disabled {{
                background-color: {colors["inactive"]};
                color: {colors["text_secondary"]};
            }}
        """
    
    @classmethod
    def get_inactive_button_style(cls, theme):
        """Get inactive button style"""
        colors = cls.get_theme(theme)
        return f"""
            QPushButton {{
                min-width: 110px;
                min-height: 36px;
                max-height: 36px;
                padding: 8px;
                border-radius: 6px;
                border: none;
                background-color: {colors["inactive"]};
                color: {colors["text_primary"]};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {colors["inactive_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {colors["inactive_pressed"]};
                min-height: 36px;
                max-height: 36px;
            }}
            QPushButton:disabled {{
                background-color: {colors["inactive"]};
                color: {colors["text_secondary"]};
                opacity: 0.5;
            }}
        """
    
    @classmethod
    def get_small_button_style(cls, theme):
        """Get style for small buttons"""
        colors = cls.get_theme(theme)
        return f"""
            QPushButton {{
                background-color: {colors["inactive"]};
                border: none;
                border-radius: 4px;
                padding: 2px;
                min-height: 22px;
                max-height: 22px;
                min-width: 22px;
                max-width: 22px;
            }}
            QPushButton:hover {{
                background-color: {colors["inactive_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {colors["inactive_pressed"]};
                min-height: 22px;
                max-height: 22px;
            }}
            QPushButton:disabled {{
                background-color: {colors["bg_secondary"]};
                color: {colors["text_secondary"]};
                opacity: 0.5;
            }}
        """
    
    @classmethod
    def get_dialog_style(cls, theme):
        """Get dialog style"""
        colors = cls.get_theme(theme)
        return f"""
            QDialog {{
                background-color: {colors["bg_primary"]};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {colors["border"]};
                border-radius: 8px;
                margin-top: 12px;
                background-color: {colors["bg_secondary"]};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {colors["text_primary"]};
            }}
            QLineEdit {{
                border: 1px solid {colors["border"]};
                border-radius: 6px;
                padding: 8px;
                background-color: {colors["bg_secondary"]};
                color: {colors["text_primary"]};
            }}
            QLineEdit:focus {{
                border: 1px solid {colors["accent"]};
            }}
            QTextEdit {{
                border: 1px solid {colors["border"]};
                border-radius: 6px;
                padding: 8px;
                background-color: {colors["bg_secondary"]};
                color: {colors["text_primary"]};
            }}
            QTextEdit:focus {{
                border: 1px solid {colors["accent"]};
            }}
        """
    
    @classmethod
    def get_transcription_item_styles(cls, theme):
        """Get transcription item styles"""
        colors = cls.get_theme(theme)
        
        # Normal small button style
        small_button_style = cls.get_small_button_style(theme)
        
        # Playing button style (for the play button when playing)
        playing_button_style = f"""
            QPushButton {{
                background-color: {colors["accent"]};
                border: none;
                border-radius: 4px;
                padding: 2px;
                min-height: 22px;
                max-height: 22px;
                min-width: 22px;
                max-width: 22px;
            }}
            QPushButton:hover {{
                background-color: {colors["accent_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {colors["accent_pressed"]};
                min-height: 22px;
                max-height: 22px;
            }}
        """
        
        return {
            "button_style": small_button_style,
            "playing_button_style": playing_button_style,
            "timestamp_style": f"color: {colors['text_secondary']}; font-weight: 600; font-family: 'Segoe UI', sans-serif;",
            "text_style": f"color: {colors['text_primary']}; font-size: 11pt; font-family: 'Segoe UI', sans-serif;",
            "ai_response_style": f"""
                color: {colors['text_primary']}; 
                background-color: {colors['bg_accent']}; 
                padding: 8px; 
                border-radius: 8px; 
                font-size: 11pt;
                font-family: 'Segoe UI', sans-serif;
                min-height: 16px;
            """
        }

class AudioProcessingWorker(QThread):
    """
    Worker thread for processing audio
    """
    def __init__(self, transcription_service):
        super().__init__()
        self.transcription_service = transcription_service
        self.running = True
    
    def run(self):
        """Run the audio processing loop"""
        logger.info("Audio processing thread started")
        
        try:
            while self.running:
                # Process audio in small chunks to keep UI responsive
                if not self.transcription_service.process_audio():
                    # If processing failed, wait a moment before retrying
                    time.sleep(0.1)
                    
                # Small sleep to prevent CPU overuse
                time.sleep(0.01)
        except Exception as e:
            logger.error(f"Error in audio processing thread: {e}", exc_info=True)
        finally:
            logger.info("Audio processing thread stopped")
    
    def stop(self):
        """Stop the audio processing thread"""
        self.running = False
        self.quit()
        self.wait()

class TranscriptionListItem(QWidget):
    """Custom widget for displaying a transcription item in the list"""
    
    def __init__(self, parent=None, theme="dark"):
        super().__init__(parent)
        self.audio_path = None
        self.is_playing = False
        self.sound = None
        self.theme = theme
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components for this widget"""
        # Get theme styles
        styles = ThemeManager.get_transcription_item_styles(self.theme)
        
        # Main layout - horizontal with gradient background
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)  # Reduced vertical padding for compact look
        main_layout.setSpacing(8)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Timestamp label with better styling
        self.timestamp_label = QLabel()
        self.timestamp_label.setStyleSheet(styles["timestamp_style"])
        self.timestamp_label.setFixedWidth(80)
        main_layout.addWidget(self.timestamp_label)
        
        # Text content - expand horizontally with better styling
        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(styles["text_style"])
        self.text_label.setMinimumHeight(16)
        # Set size policy to encourage vertical expansion for wrapped text
        self.text_label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding))
        main_layout.addWidget(self.text_label, 1)  # Add stretch factor of 1 to expand
        
        # Button container
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Copy button with icon
        self.copy_button = QPushButton()
        self.copy_button.setIcon(QIcon.fromTheme("edit-copy", QIcon("assets/copy-icon.png")))
        self.copy_button.setIconSize(QSize(14, 14))
        self.copy_button.setToolTip("Copy transcription to clipboard")
        self.copy_button.setFixedSize(22, 22)
        self.copy_button.setStyleSheet(styles["button_style"])
        button_layout.addWidget(self.copy_button)
        
        # Play button with icon
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start", QIcon("assets/play-icon.png")))
        self.play_button.setIconSize(QSize(14, 14))
        self.play_button.setToolTip("Play audio")
        self.play_button.setFixedSize(22, 22)
        self.play_button.setStyleSheet(styles["button_style"])
        self.play_button.setEnabled(False)  # Disabled by default until audio_path is set
        button_layout.addWidget(self.play_button)
        
        # Transcribe Again button with icon
        self.transcribe_button = QPushButton()
        self.transcribe_button.setIcon(QIcon.fromTheme("view-refresh", QIcon("assets/refresh-icon.png")))
        self.transcribe_button.setIconSize(QSize(14, 14))
        self.transcribe_button.setToolTip("Transcribe again")
        self.transcribe_button.setFixedSize(22, 22)
        self.transcribe_button.setStyleSheet(styles["button_style"])
        self.transcribe_button.setEnabled(False)  # Disabled by default until audio_path is set
        button_layout.addWidget(self.transcribe_button)
        
        main_layout.addLayout(button_layout)
        
        # Set a minimum width for better layout
        self.setMinimumWidth(400)
        
    def setData(self, timestamp, text, audio_path):
        """Set the data for this item"""
        self.timestamp_label.setText(f"{timestamp} >")
        self.text_label.setText(text)
        self.audio_path = audio_path
        
        # Enable/disable buttons based on audio path availability
        self.play_button.setEnabled(audio_path is not None)
        self.transcribe_button.setEnabled(audio_path is not None)
        
    def getText(self):
        """Get the current text"""
        return self.text_label.text()
        
    def updateText(self, new_text):
        """Update the displayed text"""
        self.text_label.setText(new_text)
        
    def setTheme(self, theme):
        """Update the widget's theme"""
        self.theme = theme
        styles = ThemeManager.get_transcription_item_styles(theme)
        
        # Update styles
        self.timestamp_label.setStyleSheet(styles["timestamp_style"])
        self.text_label.setStyleSheet(styles["text_style"])
        
        # Update button styles based on playing state
        if self.is_playing:
            self.play_button.setStyleSheet(styles["playing_button_style"])
        else:
            self.play_button.setStyleSheet(styles["button_style"])
            
        self.copy_button.setStyleSheet(styles["button_style"])
        self.transcribe_button.setStyleSheet(styles["button_style"])
        
    def setPlaying(self, is_playing):
        """Update the play button state"""
        self.is_playing = is_playing
        styles = ThemeManager.get_transcription_item_styles(self.theme)
        
        if is_playing:
            self.play_button.setIcon(QIcon.fromTheme("media-playback-stop", QIcon("assets/stop-icon.png")))
            self.play_button.setToolTip("Stop playback")
            self.play_button.setStyleSheet(styles["playing_button_style"])
        else:
            self.play_button.setIcon(QIcon.fromTheme("media-playback-start", QIcon("assets/play-icon.png")))
            self.play_button.setToolTip("Play audio")
            self.play_button.setStyleSheet(styles["button_style"])
        
    def stopPlayback(self):
        """Stop any active playback"""
        if self.sound and self.is_playing:
            self.sound.stop()
            self.setPlaying(False)
            self.sound = None

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
        self.theme = self.settings_manager.get('ui_theme', config.UI_THEME)
        
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
        saved_api_key = self.settings_manager.get('groq_api_key', config.GROQ_API_KEY)
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
        saved_llm_model = self.settings_manager.get('llm_model', config.LLM_MODEL)
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
        saved_transcription_model = self.settings_manager.get('transcription_model', config.TRANSCRIPTION_MODEL)
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
        saved_unfamiliar_words = self.settings_manager.get('unfamiliar_words', config.UNFAMILIAR_WORDS)
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
    
    # Rest of the methods remain the same
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

class VoiceCommanderApp(QMainWindow):
    """
    Main application window for Voice Commander
    """
    # Define some signals
    clear_chat_signal = pyqtSignal()  # Signal to clear chat from any thread
    
    def __init__(self):
        super().__init__()
        
        # Initialize settings manager before other services
        self.settings_manager = SettingsManager.SettingsManager()
        
        # Get theme from settings
        self.theme = self.settings_manager.get('ui_theme', config.UI_THEME)
        
        # Set up the window
        self.setWindowTitle("Voice Commander")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("assets/voice-commander.png"))
        
        # Apply theme-based style
        self.setStyleSheet(ThemeManager.get_main_window_style(self.theme))
        
        # Initialize attributes
        self.audio_service = None
        self.vosk_service = None
        self.transcription_service = None
        self.status_text = None
        self.chat_display = None
        self.audio_worker = None
        self.groq_service = None
        self.keyboard_service = None
        self.shortcut_buttons = {}  # Dictionary to store shortcut buttons
        
        # Connect signals
        self.clear_chat_signal.connect(self._clear_chat_display)
        
        # Initialize status_text for early logging
        self.status_text = None
        
        # Initialize services first
        self.initialize_services()
        
        # Build UI after services are initialized
        self.setup_ui()
        
        # Update UI state
        self.update_ui_state()
        
        # Load saved chat history after UI is set up
        self.load_chat_history()
        
        # Start audio processing
        self.start_audio_processing()
        
        # Set up window close handling
        self.closeEvent = self.on_close
    
    def initialize_services(self):
        """Initialize the application services"""
        logger.info("Initializing services...")
        
        # Check and install required libraries
        dependencies.check_and_install_libraries()
        
        self.vosk_service = VoskService.VoskService()
        
        # Get saved microphone settings
        saved_mic_index = self.settings_manager.get('microphone_index', 0)
        saved_mic_name = self.settings_manager.get('microphone_name', '')
        
        # Create audio service with saved microphone
        try:
            # First try by name if specified
            if saved_mic_name:
                logger.info(f"Trying to find microphone by name: {saved_mic_name}")
                self.audio_service = AudioService.AudioService(saved_mic_name)
            else:
                # Otherwise use the index
                logger.info(f"Using microphone with index: {saved_mic_index}")
                self.audio_service = AudioService.AudioService(saved_mic_index)
                
        except Exception as e:
            logger.error(f"Error initializing audio service with saved microphone: {e}")
            # Fall back to default microphone
            self.audio_service = AudioService.AudioService(None)
            self.log_status(f"Could not use saved microphone settings. Using default device.")
        
        # Create the Qt-compatible transcription service
        self.transcription_service = TranscriptionService.TranscriptionService(
            self.vosk_service, 
            self.audio_service
        )
        
        # Get a reference to the GroqWhisperService
        self.groq_service = self.transcription_service.groq_whisper_service
        
        # Apply API settings if they exist in settings
        saved_api_key = self.settings_manager.get('groq_api_key', None)
        if saved_api_key:
            self.groq_service.api_key = saved_api_key
        
        saved_llm_model = self.settings_manager.get('llm_model', None)
        if saved_llm_model:
            self.groq_service.model = saved_llm_model
        
        saved_transcription_model = self.settings_manager.get('transcription_model', None)
        if saved_transcription_model:
            self.groq_service.transcription_model = saved_transcription_model
        
        # Apply unfamiliar words if they exist in settings
        saved_unfamiliar_words = self.settings_manager.get('unfamiliar_words', None)
        if saved_unfamiliar_words:
            self.groq_service.unfamiliar_words = saved_unfamiliar_words
        
        # Initialize keyboard service
        self.keyboard_service = KeyboardService.KeyboardService(self.settings_manager)
        
        # Register shortcut callbacks
        self.keyboard_service.register_shortcut('toggle_push_to_talk', self.toggle_push_to_talk)
        self.keyboard_service.register_shortcut('toggle_recording', self.toggle_recording)
        self.keyboard_service.register_shortcut('toggle_ai_processing', self.toggle_mute)
        self.keyboard_service.register_shortcut('toggle_auto_paste', self.toggle_paste)
        
        # Connect the shortcut_triggered signal
        self.keyboard_service.shortcut_triggered.connect(self.on_shortcut_triggered)

        # Connect the keyboard_error signal to display errors to the user
        if hasattr(self.keyboard_service, 'keyboard_error'):
            self.keyboard_service.keyboard_error.connect(self.on_keyboard_error)
        
        # Load settings
        saved_language = self.settings_manager.get('language', 'en')
        saved_mute_llm = self.settings_manager.get('mute_llm', True)
        saved_automatic_paste = self.settings_manager.get('automatic_paste', True)
        
        # Apply saved settings
        self.groq_service.language = saved_language
        self.groq_service.mute_llm = saved_mute_llm
        self.groq_service.automatic_paste = saved_automatic_paste
        
        # Store a reference to the original setter
        original_setter = type(self.groq_service).language.fset
        
        def language_observer(instance, value):
            # Call the original setter
            original_setter(instance, value)
            # Update the UI on the main thread
            self.update_language_ui()
        
        # Replace the property setter with our observer
        type(self.groq_service).language = property(
            type(self.groq_service).language.fget,
            language_observer
        )
        
        # Set callbacks for GroqWhisperService commands
        self.groq_service.set_command_callbacks(
            stop_callback=self.transcription_service.pause_transcription, 
            resume_callback=self.transcription_service.resume_transcription,
            reset_callback=self.reset_chat
        )
        
        # Connect signals to slots
        self.transcription_service.transcription_result.connect(self.on_transcription_result)
        self.transcription_service.llm_response.connect(self.on_llm_response)
        self.transcription_service.status_update.connect(self.log_status)
        self.transcription_service.error.connect(self.on_error)
        self.transcription_service.audio_state_changed.connect(self.on_audio_state_changed)
        self.transcription_service.ui_state_changed.connect(self.update_ui_state)
    
    def setup_ui(self):
        """Set up the main UI components"""
        self.setWindowTitle("Voice Commander")
        self.setMinimumSize(800, 600)
        
        # Get theme colors
        colors = ThemeManager.get_theme(self.theme)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        
        # Create a splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(2)  # Thinner splitter handle
        main_layout.addWidget(splitter)
        
        # Chat area
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        # Conversation header with control buttons
        header_layout = QHBoxLayout()
        
        # Add app logo/icon to the header
        app_icon = QLabel()
        pixmap = QPixmap("assets/voice-commander.png").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        app_icon.setPixmap(pixmap)
        header_layout.addWidget(app_icon)
        
        # Add title with larger, bolder font
        chat_label = QLabel("Voice Commander")
        chat_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {colors['text_primary']};")
        header_layout.addWidget(chat_label)
        
        # Get button style
        button_style = ThemeManager.get_inactive_button_style(self.theme)
        
        # Push buttons to the right side
        header_layout.addStretch(1)
        
        # Add theme toggle button
        self.theme_button = QPushButton("Toggle Theme")
        self.theme_button.setIcon(QIcon.fromTheme("preferences-desktop-theme", QIcon("assets/theme-icon.png")))
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setStyleSheet(button_style)
        header_layout.addWidget(self.theme_button)
        
        # Add New Chat button to the conversation header
        self.reset_button = QPushButton("New Chat")
        self.reset_button.setIcon(QIcon.fromTheme("document-new", QIcon("assets/new-icon.png")))
        self.reset_button.clicked.connect(self.new_chat)
        self.reset_button.setStyleSheet(button_style)
        header_layout.addWidget(self.reset_button)
        
        # Add the header to the chat layout
        chat_layout.addLayout(header_layout)
        
        # Replace QTextEdit with QListWidget for transcriptions
        self.chat_display = QListWidget()
        self.chat_display.setAlternatingRowColors(True)
        self.chat_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_display.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {colors['border']};
                border-radius: 8px;
                background-color: {colors['bg_secondary']};
                alternate-background-color: {colors['bg_primary']};
                padding: 2px;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {colors['border']};
                padding: 1px;
                border-radius: 6px;
            }}
            QListWidget::item:hover {{
                background-color: {colors['bg_accent']};
            }}
        """)
        self.chat_display.setFont(QFont("Segoe UI", 11))
        self.chat_display.setSpacing(0)
        self.chat_display.setWordWrap(True)
        chat_layout.addWidget(self.chat_display)
        
        splitter.addWidget(chat_container)
        
        # Controls area
        controls_container = QWidget()
        controls_container.setStyleSheet(f"background-color: {colors['bg_primary']};")
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setSpacing(10)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Define active and inactive button styles from ThemeManager
        active_button_style = ThemeManager.get_active_button_style(self.theme)
        inactive_button_style = ThemeManager.get_inactive_button_style(self.theme)
        
        # Group the controls in a grid layout
        controls_group = QGroupBox("Controls")
        controls_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {colors['border']};
                border-radius: 8px;
                margin-top: 12px;
                background-color: {colors['bg_secondary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {colors['text_primary']};
            }}
        """)
        controls_grid = QGridLayout()
        controls_grid.setVerticalSpacing(15)
        controls_grid.setHorizontalSpacing(15)
        controls_grid.setContentsMargins(15, 15, 15, 15)
        
        # Row 1: Recording, AI and Paste buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)  # Increase spacing between buttons
        
        # Recording control button
        self.record_button = QPushButton("Start Transcription")
        self.record_button.setIcon(QIcon.fromTheme("media-record", QIcon("assets/record-icon.png")))
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet(inactive_button_style)  # Will be updated in update_ui_state()
        button_layout.addWidget(self.record_button)
        
        # Push to Talk button
        self.push_to_talk_button = QPushButton("Push to Talk")
        self.push_to_talk_button.setIcon(QIcon.fromTheme("audio-input-microphone", QIcon("assets/mic-icon.png")))
        self.push_to_talk_button.clicked.connect(self.toggle_push_to_talk)
        self.push_to_talk_button.setStyleSheet(inactive_button_style)  # Will be updated in update_ui_state()
        button_layout.addWidget(self.push_to_talk_button)
        
        # LLM processing toggle button
        self.mute_button = QPushButton("AI Processing: On")
        self.mute_button.setIcon(QIcon.fromTheme("system-run", QIcon("assets/ai-icon.png")))
        self.mute_button.clicked.connect(self.toggle_mute)
        self.mute_button.setStyleSheet(inactive_button_style)  # Will be updated in update_ui_state()
        button_layout.addWidget(self.mute_button)
        
        # Automatic paste toggle button
        self.paste_button = QPushButton("Auto-Paste: On")
        self.paste_button.setIcon(QIcon.fromTheme("edit-paste", QIcon("assets/paste-icon.png")))
        self.paste_button.clicked.connect(self.toggle_paste)
        self.paste_button.setStyleSheet(inactive_button_style)  # Will be updated in update_ui_state()
        button_layout.addWidget(self.paste_button)
        
        # Create a widget to hold the button layout
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        
        # Add the button widget to the grid layout
        controls_grid.addWidget(button_widget, 0, 0, 1, 3)
        
        # Row 2: Language selection with Settings button
        selections_layout = QHBoxLayout()
        selections_layout.setContentsMargins(0, 0, 0, 0)  # Reduce margins
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(120)  # Match button width
        
        # Add languages from config
        for code, name in config.AVAILABLE_LANGUAGES.items():
            self.language_combo.addItem(name, code)
            
        # Set current language from settings
        saved_language = self.settings_manager.get('language', 'en')
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == saved_language:
                self.language_combo.setCurrentIndex(i)
                break
                
        self.language_combo.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.language_combo)
        
        # Add Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.setIcon(QIcon.fromTheme("preferences-system", QIcon("assets/settings-icon.png")))
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.settings_button.setStyleSheet(button_style)
        lang_layout.addWidget(self.settings_button)
        
        # Add language selection to the combined layout
        selections_layout.addLayout(lang_layout)
        
        # Add the combined selections to the grid
        controls_grid.addLayout(selections_layout, 1, 0, 1, 3)
        
        # Set the grid layout to the controls group
        controls_group.setLayout(controls_grid)
        controls_layout.addWidget(controls_group)
        
        # Status area
        status_group = QGroupBox("Status")
        status_group.setStyleSheet(f"""
            QGroupBox {{ 
                padding-top: 15px; 
                margin-top: 5px; 
                background-color: {colors['bg_secondary']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {colors['text_primary']};
            }}
        """)
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(80)  # Slightly reduce maximum height
        status_layout.addWidget(self.status_text)
        
        status_group.setLayout(status_layout)
        controls_layout.addWidget(status_group)
        
        # Add controls to splitter
        splitter.addWidget(controls_container)
        
        # Set the splitter's initial sizes (70% chat, 30% controls)
        splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])
        
        # Update UI based on current state
        self.update_ui_state()
    
    def populate_microphones(self):
        """Populate the microphone selection dropdown"""
        # This method is kept for backward compatibility
        # It's no longer used in the main window but may be called elsewhere
        if hasattr(self, 'microphone_combo'):
            self.microphone_combo.clear()
            
            # Add all available microphones
            for device_id, device_name in self.audio_service.device_list:
                self.microphone_combo.addItem(f"{device_name}", device_id)
    
    def update_ui_state(self):
        """Update UI elements based on current application state"""
        # Define active button style (blue)
        active_button_style = """
            QPushButton {
                min-width: 110px;
                min-height: 36px;
                max-height: 36px;
                padding: 8px;
                border-radius: 6px;
                border: none;
                background-color: #5b87f7;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4a76e6;
            }
            QPushButton:pressed {
                background-color: #3a65d5;
                min-height: 36px;
                max-height: 36px;
            }
            QPushButton:disabled {
                background-color: #d1d6e6;
                color: #9aa3bc;
            }
        """
        
        # Inactive button style
        inactive_button_style = """
            QPushButton {
                min-width: 110px;
                min-height: 36px;
                max-height: 36px;
                padding: 8px;
                border-radius: 6px;
                border: none;
                background-color: #f1f3fa;
                color: #505a7a;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #e1e5ee;
            }
            QPushButton:pressed {
                background-color: #d1d6e6;
                min-height: 36px;
                max-height: 36px;
            }
            QPushButton:disabled {
                background-color: #f5f7fd;
                color: #a8b3d2;
            }
        """
        
        # Update recording button - only show active when recording
        is_recording = self.transcription_service.is_transcribing
        is_push_to_talk = self.transcription_service.is_push_to_talk_mode
        self.record_button.setText("Recording" if is_recording else "Start Transcription")
        self.record_button.setStyleSheet(active_button_style if is_recording else inactive_button_style)
        # Disable the record button when push-to-talk is active
        self.record_button.setEnabled(not is_push_to_talk)
        
        # Update push to talk button
        self.push_to_talk_button.setText("Stop Talking" if is_push_to_talk else "Push to Talk")
        self.push_to_talk_button.setStyleSheet(active_button_style if is_push_to_talk else inactive_button_style)
        
        # Update mute button
        is_muted = self.groq_service.mute_llm
        self.mute_button.setText(f"AI Processing: {'Off' if is_muted else 'On'}")
        self.mute_button.setStyleSheet(inactive_button_style if is_muted else active_button_style)
        
        # Update paste button
        is_paste_on = self.groq_service.automatic_paste
        self.paste_button.setText(f"Auto-Paste: {'On' if is_paste_on else 'Off'}")
        self.paste_button.setStyleSheet(active_button_style if is_paste_on else inactive_button_style)
    
    def start_audio_processing(self):
        """Start the audio processing thread"""
        # Start the transcription service
        self.transcription_service.start_transcription()
        
        # Create and start the audio processing worker
        self.audio_worker = AudioProcessingWorker(self.transcription_service)
        self.audio_worker.start()
        
        self.log_status("Audio processing initialized.")
    
    @pyqtSlot(dict)  # Updated to receive dict instead of str
    def on_transcription_result(self, result_data):
        """Handle new transcription result"""
        # Extract data from the dictionary
        timestamp = result_data.get('timestamp', '')
        text = result_data.get('text', '')
        audio_path = result_data.get('audio_path')
        
        # Add as a transcription item
        self.add_transcription_item(timestamp, text, audio_path)
        
        # Save chat history after adding a new item
        self.save_chat_history()
    
    @pyqtSlot(str)
    def on_llm_response(self, text):
        """Handle LLM response"""
        self.add_ai_response(text)
    
    @pyqtSlot(str)
    def on_error(self, error_msg):
        """Handle error message"""
        self.log_status(f"ERROR: {error_msg}")
    
    @pyqtSlot(bool)
    def on_audio_state_changed(self, is_recording):
        """Handle audio state change"""
        self.record_button.setText("Recording" if is_recording else "Start Transcription")
    
    def add_transcription_item(self, timestamp, text, audio_path):
        """Add a user transcription as a custom list item"""
        # Create the custom widget
        item_widget = TranscriptionListItem()
        item_widget.setData(timestamp, text, audio_path)
        
        # Connect button signals
        # Connect copy button signal
        item_widget.copy_button.clicked.connect(
            lambda: self.copy_to_clipboard(text)
        )
        
        if audio_path:
            # Important: Use lambda instead of partial to ensure we get the current state
            item_widget.play_button.clicked.connect(
                lambda: self.play_audio(audio_path, item_widget)
            )
            item_widget.transcribe_button.clicked.connect(
                lambda: self.retranscribe_audio(audio_path, item_widget)
            )
        
        # Create a list item and set its size
        list_item = QListWidgetItem(self.chat_display)
        
        # Add the widget to the list item
        self.chat_display.addItem(list_item)
        self.chat_display.setItemWidget(list_item, item_widget)
        # Explicitly set the item hint based on the widget's calculated hint
        list_item.setSizeHint(item_widget.sizeHint())
        
        # Scroll to the new item
        self.chat_display.scrollToItem(list_item)
    
    def add_ai_response(self, text):
        """Add an AI response message to the chat display"""
        # Create a container widget for the AI response
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 4, 8, 4)  # Further reduced vertical padding from 6px to 4px
        
        # Create a QLabel for the AI response with better styling
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("""
            color: #505a7a; 
            background-color: #eef1fa; 
            padding: 8px; 
            border-radius: 8px; 
            font-size: 11pt;
            font-family: 'Segoe UI', sans-serif;
            min-height: 16px;
        """)
        # Set size policy to encourage vertical expansion for wrapped text
        label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding))
        container_layout.addWidget(label)
        
        # Create a list item and set its size
        list_item = QListWidgetItem(self.chat_display)
        
        # Add the widget to the list item
        self.chat_display.addItem(list_item)
        self.chat_display.setItemWidget(list_item, container)
        # Explicitly set the item hint based on the widget's calculated hint
        list_item.setSizeHint(container.sizeHint())
        
        # Scroll to the new item
        self.chat_display.scrollToItem(list_item)
    
    def log_status(self, message):
        """Add a message to the status log"""
        # If status_text isn't initialized yet, just print to console
        if self.status_text is None:
            logger.info(message)
            print(message)
            return
            
        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(f"{message}\n")
        
        # Scroll to bottom
        self.status_text.setTextCursor(cursor)
        self.status_text.ensureCursorVisible()
    
    # UI event handlers
    def toggle_recording(self):
        """Toggle the recording state"""
        # If push-to-talk is active, deactivate it first
        if self.transcription_service.is_push_to_talk_mode:
            self.toggle_push_to_talk()
            
        if self.transcription_service.is_transcribing:
            self.transcription_service.pause_transcription()
        else:
            self.transcription_service.resume_transcription()
    
    def toggle_push_to_talk(self):
        """Toggle push-to-talk mode and update the UI"""
        # Call the transcription service method
        self.transcription_service.toggle_push_to_talk()
        
        # Update the UI state to reflect current state
        self.update_ui_state()
        
        # Log status change
        is_active = self.transcription_service.is_push_to_talk_mode
        status = "activated" if is_active else "deactivated"
        self.log_status(f"Push-to-talk mode {status}")
    
    def toggle_mute(self):
        """Toggle LLM mute state"""
        self.groq_service.mute_llm = not self.groq_service.mute_llm
        status = "disabled" if self.groq_service.mute_llm else "enabled"
        self.log_status(f"AI chat {status}")
        
        # Save the setting
        self.settings_manager.set('mute_llm', self.groq_service.mute_llm)
        
        # Only attempt TTS if we're unmuting or were not muted before
        if not self.groq_service.mute_llm:
            try:
                self.groq_service.safe_tts_say(f"AI {status}")
            except Exception as e:
                self.log_status(f"TTS error: {e}")
        
        self.update_ui_state()
    
    def toggle_paste(self):
        """Toggle paste state"""
        self.groq_service.automatic_paste = not self.groq_service.automatic_paste
        status = "enabled" if self.groq_service.automatic_paste else "disabled"
        self.log_status(f"Automatic paste {status}")
        
        # Save the setting
        self.settings_manager.set('automatic_paste', self.groq_service.automatic_paste)
        
        # Only attempt TTS if not muted
        if not self.groq_service.mute_llm:
            try:
                self.groq_service.safe_tts_say(f"Automatic paste {status}")
            except Exception as e:
                self.log_status(f"TTS error: {e}")
        
        self.update_ui_state()
    
    def new_chat(self):
        """Clear the chat history and start a new chat"""
        try:
            # Reset the chat history in the service
            self.groq_service.InitializeChat()
            self.log_status("New chat started")
            
            # Emit signal to clear chat display in the UI thread
            self.clear_chat_signal.emit()
            
            # Only attempt TTS if not muted
            if not self.groq_service.mute_llm:
                try:
                    self.groq_service.safe_tts_say("New chat started")
                except Exception as e:
                    self.log_status(f"TTS error: {e}")
                    
            # Save the empty chat history
            self.save_chat_history()
        except Exception as e:
            self.log_status(f"Error starting new chat: {e}")
            logger.error(f"Error in new_chat: {e}", exc_info=True)
    
    # Maintain backward compatibility
    def reset_chat(self):
        """Alias for new_chat for backward compatibility"""
        self.new_chat()
    
    def change_language(self, index):
        """Change the language based on combo box selection"""
        if index < 0:
            return
            
        # Get the language code from the current selection
        lang_code = self.language_combo.itemData(index)
        if lang_code:
            # Update the language in the service
            self.groq_service.language = lang_code
            
            # Save the selection to settings
            self.settings_manager.set('language', lang_code)
            
            # Log the change
            lang_name = self.language_combo.itemText(index)
            self.log_status(f"Language switched to {lang_name}")
            
            # Only attempt TTS if not muted
            if not self.groq_service.mute_llm:
                try:
                    self.groq_service.safe_tts_say(f"Language switched to {lang_name}")
                except Exception as e:
                    self.log_status(f"TTS error: {e}")
    
    def change_microphone(self, index):
        """Change the microphone based on combo box selection"""
        if index < 0:
            return
            
        # Get the device index from the current selection
        device_index = self.microphone_combo.itemData(index)
        if device_index is not None:
            # Get the device name for logging
            device_name = self.microphone_combo.itemText(index)
            
            # Stop audio processing temporarily
            if hasattr(self, 'audio_worker'):
                self.audio_worker.stop()
                
            # Pause transcription
            was_transcribing = self.transcription_service.is_transcribing
            if was_transcribing:
                self.transcription_service.pause_transcription()
            
            # Switch the device
            if self.audio_service.switch_device(device_index):
                # Save the selection to settings
                self.settings_manager.set('microphone_index', device_index)
                self.settings_manager.set('microphone_name', device_name)
                
                # Log the change
                self.log_status(f"Microphone switched to {device_name}")
                
                # Important: We need to recreate the recognizer with the new device's parameters
                self.transcription_service.reset_recognizer()
                
                # Wait a moment for audio system to stabilize
                time.sleep(0.5)
                
                # Restart audio processing
                self.start_audio_processing()
                
                # Resume transcription if it was active
                if was_transcribing:
                    self.transcription_service.resume_transcription()
            else:
                self.log_status(f"Failed to switch to microphone: {device_name}")
                
                # Try to select the current device in the UI
                current_device = self.audio_service.device_index
                for i in range(self.microphone_combo.count()):
                    if self.microphone_combo.itemData(i) == current_device:
                        # Block signals to avoid triggering change_microphone again
                        self.microphone_combo.blockSignals(True)
                        self.microphone_combo.setCurrentIndex(i)
                        self.microphone_combo.blockSignals(False)
                        break
    
    def _clear_chat_display(self):
        """Slot for clearing the chat display in the UI thread"""
        if self.chat_display:
            self.chat_display.clear()
    
    def on_close(self, event):
        """Handle window close event"""
        try:
            # Save the chat history before closing
            self.save_chat_history()
            
            # Save window position and size
            self.settings_manager.set('window_position', [self.x(), self.y()])
            self.settings_manager.set('window_size', [self.width(), self.height()])
            
            # Stop the audio worker
            if hasattr(self, 'audio_worker'):
                self.audio_worker.stop()
            
            # Stop the transcription service
            if hasattr(self, 'transcription_service'):
                self.transcription_service.stop_transcription()
            
            # Stop the keyboard listener
            if hasattr(self, 'keyboard_service') and self.keyboard_service:
                logger.info("Stopping keyboard service")
                self.keyboard_service.stop_listening()
                # Make sure all keyboard data is saved
                self.keyboard_service.save_shortcuts()
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}", exc_info=True)
        
        # Accept the close event
        event.accept()

    def update_language_ui(self):
        """Update the language selection UI based on the current service setting"""
        if not hasattr(self, 'language_combo') or not self.language_combo:
            return
            
        # Find the index for the current language
        current_lang = self.groq_service.language
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_lang:
                # Block signals to prevent recursive calls
                self.language_combo.blockSignals(True)
                self.language_combo.setCurrentIndex(i)
                self.language_combo.blockSignals(False)
                break

    def open_settings_dialog(self):
        """Open the settings dialog"""
        settings_dialog = SettingsDialog(
            self, 
            self.settings_manager, 
            self.keyboard_service,
            self.audio_service,
            self.groq_service
        )
        
        # Show the dialog and wait for user to finish
        if settings_dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply microphone changes if needed
            new_mic_index = settings_dialog.get_selected_microphone()
            current_mic_index = self.audio_service.device_index
            
            if new_mic_index is not None and new_mic_index != current_mic_index:
                # Get the device name for logging
                device_name = ""
                for i in range(settings_dialog.microphone_combo.count()):
                    if settings_dialog.microphone_combo.itemData(i) == new_mic_index:
                        device_name = settings_dialog.microphone_combo.itemText(i)
                        break
                
                # Stop audio processing temporarily
                if hasattr(self, 'audio_worker'):
                    self.audio_worker.stop()
                    
                # Pause transcription
                was_transcribing = self.transcription_service.is_transcribing
                if was_transcribing:
                    self.transcription_service.pause_transcription()
                
                # Switch the device
                if self.audio_service.switch_device(new_mic_index):
                    # Save the selection to settings
                    self.settings_manager.set('microphone_index', new_mic_index)
                    self.settings_manager.set('microphone_name', device_name)
                    
                    # Log the change
                    self.log_status(f"Microphone switched to {device_name}")
                    
                    # Important: We need to recreate the recognizer with the new device's parameters
                    self.transcription_service.reset_recognizer()
                    
                    # Wait a moment for audio system to stabilize
                    time.sleep(0.5)
                    
                    # Restart audio processing
                    self.start_audio_processing()
                    
                    # Resume transcription if it was active
                    if was_transcribing:
                        self.transcription_service.resume_transcription()
                else:
                    self.log_status(f"Failed to switch to microphone: {device_name}")

    def play_audio(self, audio_path, item_widget):
        """Play or stop the audio file at the given path"""
        # If the item is already playing, stop it and exit
        if item_widget.is_playing:
            item_widget.stopPlayback()
            self.log_status("Playback stopped")
            return
            
        # At this point we're starting a new playback, so first stop any other playback
        self.stop_all_playback()
            
        if not audio_path or not os.path.exists(audio_path):
            self.log_status(f"Error: Audio file not found at {audio_path}")
            return
            
        try:
            # Use pygame mixer to play the audio file
            sound = pygame.mixer.Sound(audio_path)
            
            # Play the sound
            sound.play()
            
            # Store the sound in the widget
            item_widget.sound = sound
            item_widget.setPlaying(True)
                
            # Schedule a check to see when the sound finishes playing
            def check_if_still_playing():
                if not pygame.mixer.get_busy() and item_widget.is_playing:
                    item_widget.setPlaying(False)
                    item_widget.sound = None
            
            # Check every 100ms if the sound is still playing
            timer = QTimer(self)
            timer.timeout.connect(check_if_still_playing)
            timer.start(100)
                
            self.log_status(f"Playing audio: {os.path.basename(audio_path)}")
        except Exception as e:
            self.log_status(f"Error playing audio: {e}")
    
    def stop_all_playback(self):
        """Stop all currently playing audio"""
        # Stop all pygame channels
        pygame.mixer.stop()
        
        # Reset all item widgets that might be in playing state
        for i in range(self.chat_display.count()):
            item = self.chat_display.item(i)
            widget = self.chat_display.itemWidget(item)
            if hasattr(widget, 'is_playing') and widget.is_playing:
                widget.setPlaying(False)
                widget.sound = None
    
    def retranscribe_audio(self, audio_path, item_widget):
        """Re-transcribe the audio file at the given path"""
        if not audio_path or not os.path.exists(audio_path):
            self.log_status(f"Error: Audio file not found at {audio_path}")
            return
            
        try:
            # Read the audio file
            with wave.open(audio_path, 'rb') as wf:
                # Get the audio data
                audio_data = wf.readframes(wf.getnframes())
            
            # Use the transcription service to re-transcribe
            new_text = self.transcription_service.groq_whisper_service.TranscribeAudio(audio_data)
            
            if new_text:
                # Update the widget with the new transcription
                item_widget.updateText(new_text)
                
                # Adjust the size of the list item to fit the new text
                # Find the list item that contains this widget
                for i in range(self.chat_display.count()):
                    list_item = self.chat_display.item(i)
                    if self.chat_display.itemWidget(list_item) == item_widget:
                        # The size should now be determined automatically by the widget's sizeHint.
                        # list_item.setSizeHint(QSize(self.chat_display.width(), item_height))
                        # Update the item hint based on the widget's recalculated hint
                        list_item.setSizeHint(item_widget.sizeHint())
                        break
                
                self.log_status(f"Re-transcribed audio: {new_text}")
            else:
                self.log_status("Transcription failed")
        except Exception as e:
            self.log_status(f"Error re-transcribing audio: {e}")

    def save_chat_history(self):
        """Save the current chat history to disk"""
        try:
            chat_history = []
            
            # Extract data from each item in the chat display
            for i in range(self.chat_display.count()):
                item = self.chat_display.item(i)
                widget = self.chat_display.itemWidget(item)
                
                if isinstance(widget, TranscriptionListItem):
                    # User transcription
                    chat_history.append({
                        'type': 'user',
                        'timestamp': widget.timestamp_label.text().strip(' >'),
                        'text': widget.text_label.text(),
                        'audio_path': widget.audio_path
                    })
                else:
                    # AI response - identify by looking for a QLabel inside the widget's layout
                    try:
                        ai_label = None
                        # Find the QLabel in the widget's layout
                        for j in range(widget.layout().count()):
                            child = widget.layout().itemAt(j).widget()
                            if isinstance(child, QLabel):
                                ai_label = child
                                break
                        
                        if ai_label:
                            chat_history.append({
                                'type': 'ai',
                                'text': ai_label.text()
                            })
                    except (AttributeError, Exception) as e:
                        # Skip if we can't extract text from this widget
                        logger.warning(f"Could not extract AI response from widget: {e}")
                        continue
            
            # Save to a file in the settings directory
            settings_dir = os.path.dirname(self.settings_manager.settings_path)
            chat_history_path = os.path.join(
                settings_dir, 
                'voice_commander_chat_history.json'
            )
            
            with open(chat_history_path, 'w', encoding='utf-8') as f:
                json.dump(chat_history, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Chat history saved with {len(chat_history)} items")
            
        except Exception as e:
            logger.error(f"Error saving chat history: {e}", exc_info=True)
    
    def load_chat_history(self):
        """Load chat history from disk"""
        try:
            # Path to the chat history file
            settings_dir = os.path.dirname(self.settings_manager.settings_path)
            chat_history_path = os.path.join(
                settings_dir, 
                'voice_commander_chat_history.json'
            )
            
            # If the file doesn't exist, nothing to load
            if not os.path.exists(chat_history_path):
                logger.info("No chat history file found")
                return
            
            # Load the chat history data
            with open(chat_history_path, 'r', encoding='utf-8') as f:
                chat_history = json.load(f)
            
            # Clear current chat display
            self.chat_display.clear()
            
            # Add each item to the display
            for item in chat_history:
                item_type = item.get('type', 'user')  # Default to user type for backward compatibility
                
                if item_type == 'user':
                    # User transcription
                    timestamp = item.get('timestamp', '')
                    text = item.get('text', '')
                    audio_path = item.get('audio_path')
                    
                    # Verify audio path exists
                    if audio_path and not os.path.exists(audio_path):
                        logger.warning(f"Audio file not found: {audio_path}")
                        audio_path = None
                    
                    self.add_transcription_item(timestamp, text, audio_path)
                elif item_type == 'ai':
                    # AI response
                    text = item.get('text', '')
                    self.add_ai_response(text)
            
            logger.info(f"Loaded chat history with {len(chat_history)} items")
            
        except Exception as e:
            logger.error(f"Error loading chat history: {e}", exc_info=True)

    # Add back the legacy method for compatibility
    def add_chat_message(self, text, is_user=True):
        """Legacy method maintained for compatibility"""
        if is_user and isinstance(text, dict):
            # Handle new format
            timestamp = text.get('timestamp', '')
            message = text.get('text', '')
            audio_path = text.get('audio_path')
            self.add_transcription_item(timestamp, message, audio_path)
        elif is_user and isinstance(text, str):
            # Try to extract timestamp and message from string format "HH:MM:SS > message"
            parts = text.split('>', 1)
            if len(parts) == 2:
                timestamp = parts[0].strip()
                message = parts[1].strip()
                self.add_transcription_item(timestamp, message, None)
            else:
                # Fallback
                self.add_transcription_item(datetime.now().strftime("%H:%M:%S"), text, None)
        else:
            # AI response
            self.add_ai_response(text)

    def copy_to_clipboard(self, text):
        """Copy the given text to clipboard"""
        try:
            pyperclip.copy(text)
            self.log_status(f"Copied to clipboard: {text[:30]}..." if len(text) > 30 else f"Copied to clipboard: {text}")
        except Exception as e:
            self.log_status(f"Error copying to clipboard: {e}")

    def on_shortcut_triggered(self, action_name):
        """Handle when a keyboard shortcut is triggered"""
        logger.info(f"Shortcut triggered for action: {action_name}")
        
        # Log the shortcut usage to the status
        shortcut_key = self.keyboard_service.get_shortcut(action_name)
        
        # Try to get a friendly name for display
        display_key = shortcut_key
        if shortcut_key and (shortcut_key.startswith("vk") or shortcut_key.startswith("Key_0x")):
            display_key = self.keyboard_service.get_friendly_key_name(shortcut_key)
            
        self.log_status(f"Keyboard shortcut [{display_key}] activated: {action_name}")
        
        # No need to do anything here as the action is directly connected to the method
        # The methods will be called directly by the keyboard service
        
    def on_keyboard_error(self, error_msg):
        """Handle keyboard service errors"""
        self.log_status(f"Keyboard error: {error_msg}")
        # Show error in status bar for a short time
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f"Keyboard error: {error_msg}", 5000)

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        # Toggle theme
        new_theme = "light" if self.theme == "dark" else "dark"
        self.change_theme(new_theme)
        
        # Log the change
        self.log_status(f"Switched to {new_theme} theme")
    
    def change_theme(self, new_theme):
        """Change the application theme"""
        # Save theme to settings
        self.settings_manager.set('ui_theme', new_theme)
        self.theme = new_theme
        
        # Apply new theme to main window
        self.setStyleSheet(ThemeManager.get_main_window_style(new_theme))
        
        # Update button styles in UI
        self.update_ui_state()
        
        # Update the chat display style
        colors = ThemeManager.get_theme(new_theme)
        self.chat_display.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {colors['border']};
                border-radius: 8px;
                background-color: {colors['bg_secondary']};
                alternate-background-color: {colors['bg_primary']};
                padding: 2px;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {colors['border']};
                padding: 1px;
                border-radius: 6px;
            }}
            QListWidget::item:hover {{
                background-color: {colors['bg_accent']};
            }}
        """)
        
        # Update theme for all transcription items
        self.update_transcription_item_themes()
        
        # Update status text style
        self.status_text.setStyleSheet(f"""
            border: 1px solid {colors['border']};
            border-radius: 8px;
            background-color: {colors['bg_secondary']};
            selection-background-color: {colors['accent']};
            selection-color: white;
            color: {colors['text_primary']};
        """)
        
        # Update theme for groupboxes
        for group_box in self.findChildren(QGroupBox):
            group_box.setStyleSheet(f"""
                QGroupBox {{
                    font-weight: bold;
                    border: 1px solid {colors['border']};
                    border-radius: 8px;
                    margin-top: 12px;
                    background-color: {colors['bg_secondary']};
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    color: {colors['text_primary']};
                }}
            """)
    
    def update_transcription_item_themes(self):
        """Update the theme for all transcription items in the chat display"""
        for i in range(self.chat_display.count()):
            item = self.chat_display.item(i)
            widget = self.chat_display.itemWidget(item)
            
            # Update TranscriptionListItem widgets
            if hasattr(widget, 'setTheme'):
                widget.setTheme(self.theme)
            
            # Update AI response container widgets
            elif isinstance(widget, QWidget) and widget.layout():
                for j in range(widget.layout().count()):
                    child = widget.layout().itemAt(j).widget()
                    if isinstance(child, QLabel):
                        # This is an AI response, update its style
                        styles = ThemeManager.get_transcription_item_styles(self.theme)
                        child.setStyleSheet(styles["ai_response_style"])

def main():
    """Main entry point for the Qt application"""
    # Enable high DPI scaling
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    print("Voice Commander Qt v0.3.0\n")
    print("Starting the Qt-based Voice Commander application...")
    
    import argparse
    parser = argparse.ArgumentParser(description="Voice Commander")
    parser.add_argument("-d", "--device", help="Audio input device index or name substring to use")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    config.VERBOSE_OUTPUT = args.verbose
    
    # Configure logging levels based on verbose flag
    if not config.VERBOSE_OUTPUT:
        logging.getLogger('httpx').setLevel(logging.WARNING)
    
    app = QApplication(sys.argv)
    
    # If device is specified on command line, update settings before creating the app
    if args.device is not None:
        settings_manager = SettingsManager.SettingsManager()
        try:
            # Try to convert to integer if it's a number
            device_index = int(args.device)
            settings_manager.set('microphone_index', device_index)
            print(f"Using command line specified device index: {device_index}")
        except ValueError:
            # It's a string, store it to be searched by name during initialization
            settings_manager.set('microphone_name', args.device)
            print(f"Using command line specified device name: {args.device}")
    
    window = VoiceCommanderApp()
    
    # Restore window position and size if available
    settings_manager = SettingsManager.SettingsManager()
    position = settings_manager.get('window_position')
    size = settings_manager.get('window_size')
    
    if position and len(position) == 2:
        window.move(position[0], position[1])
    
    if size and len(size) == 2:
        window.resize(size[0], size[1])
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 