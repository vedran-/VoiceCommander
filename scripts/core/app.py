import sys
import os
import logging
import time
import json
import platform
import pygame
import wave
import pyperclip
from datetime import datetime
from functools import partial
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QTextEdit, QLabel, QComboBox, QSplitter, QGroupBox, QGridLayout, QScrollArea,
                            QListWidget, QListWidgetItem, QDialog, QSizePolicy)
from PyQt6.QtCore import (Qt, QThread, pyqtSignal, pyqtSlot, QMetaObject, QTimer, QPoint, 
                          QSettings, QSize)
from PyQt6.QtGui import (QColor, QTextCursor, QFont, QIcon, QPalette, QAction, QPixmap)

# Import UI components
from ..ui.theme import ThemeManager
from ..ui.transcription_item import TranscriptionListItem
from ..ui.settings_dialog import SettingsDialog

# Import audio components
from ..audio.worker import AudioProcessingWorker

# Import services
from .. import VoskService
from .. import AudioService
from .. import TranscriptionService
from .. import SettingsManager
from .. import KeyboardService
from .. import config
from .. import dependencies

# Import pynput for keyboard capture
try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None
    logging.error("pynput library not found. Cannot capture keyboard shortcuts.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('VoiceCommander')

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
        
        # Apply theme-based style after UI is fully set up (will be done in setup_ui)
        # Theme styling is now deferred until after UI is created
        
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
        
        # Fully apply the theme to all components now that UI is created
        self.change_theme(self.theme)
        
        # Update UI state
        self.update_ui_state()
        
        # Load saved chat history after UI is set up
        self.load_chat_history()
        
        # Connect closeEvent handler
        self.closeEvent = self.on_close
        
        # Start audio processing
        self.start_audio_processing()
        
        # Log application startup
        self.log_status("Voice Commander initialized. Ready for commands.")
    
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
        
        # Add app logo/icon to the header - using actual app icon instead of PNG
        app_icon = QLabel()
        # Use fully transparent background (both in light and dark themes)
        app_icon.setStyleSheet("background-color: transparent;")
        app_icon.setText("🎤")  # Simple microphone icon
        header_layout.addWidget(app_icon)
        
        # Add title with larger, bolder font and transparent background
        chat_label = QLabel("Voice Commander")
        chat_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #505a7a; background-color: transparent;")
        header_layout.addWidget(chat_label)
        
        # Get button style
        button_style = ThemeManager.get_inactive_button_style(self.theme)
        
        # Push buttons to the right side
        header_layout.addStretch(1)
        
        # Add New Chat button to the conversation header
        self.reset_button = QPushButton("New Chat")
        self.reset_button.setText("🔄 New Chat")  # Unicode refresh icon
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
        self.controls_container = QWidget()
        self.controls_container.setStyleSheet(f"background-color: {colors['bg_primary']};")
        controls_layout = QVBoxLayout(self.controls_container)
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
        self.record_button = QPushButton(" Recording")
        self.record_button.setText("⏺️ Start Transcription")  # Unicode record icon
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet(inactive_button_style)  # Will be updated in update_ui_state()
        button_layout.addWidget(self.record_button)
        
        # Push to Talk button
        self.push_to_talk_button = QPushButton("Push to Talk")
        self.push_to_talk_button.setText("🎤 Push to Talk")  # Unicode microphone icon
        self.push_to_talk_button.clicked.connect(self.toggle_push_to_talk)
        self.push_to_talk_button.setStyleSheet(inactive_button_style)  # Will be updated in update_ui_state()
        button_layout.addWidget(self.push_to_talk_button)
        
        # LLM processing toggle button
        self.mute_button = QPushButton("AI Processing: On")
        self.mute_button.setText("🤖 AI Processing: On")  # Unicode robot icon
        self.mute_button.clicked.connect(self.toggle_mute)
        self.mute_button.setStyleSheet(inactive_button_style)  # Will be updated in update_ui_state()
        button_layout.addWidget(self.mute_button)
        
        # Automatic paste toggle button
        self.paste_button = QPushButton("Auto-Paste: On")
        self.paste_button.setText("📋 Auto-Paste: On")  # Unicode clipboard icon
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
        lang_label = QLabel("Language:")
        lang_label.setStyleSheet(f"background-color: {colors['bg_secondary']}; color: {colors['text_primary']};")
        lang_layout.addWidget(lang_label)
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
        
        # Add Settings button that opens the settings dialog
        self.settings_button = QPushButton("Settings")
        self.settings_button.setText("⚙️ Settings")  # Unicode gear icon
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
        splitter.addWidget(self.controls_container)
        
        # Set the splitter's initial sizes (70% chat, 30% controls)
        splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])
        
        # Update UI based on current state
        self.update_ui_state()
        
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
        
        # Get theme colors for direct widget styling
        colors = ThemeManager.get_theme(new_theme)
        
        # Explicitly style central widget to ensure main background color is applied
        self.centralWidget().setStyleSheet(f"background-color: {colors['bg_primary']};")
        
        # Update button styles in UI
        self.update_ui_state()
        
        # Apply theme to all widgets recursively
        self.apply_theme_to_all_widgets(self, new_theme, colors)
        
        # Update the transcription item themes separately as they need special handling
        self.update_transcription_item_themes()
        
        # Log the change
        self.log_status(f"Switched to {new_theme} theme")
        
    def apply_theme_to_all_widgets(self, parent_widget, theme, colors):
        """Recursively apply theme to all widgets"""
        # Explicitly style key container widgets
        self.centralWidget().setStyleSheet(f"background-color: {colors['bg_primary']};")
        self.controls_container.setStyleSheet(f"background-color: {colors['bg_primary']};")
        
        # Process all child widgets
        for child in parent_widget.findChildren(QWidget):
            # Apply specific styling based on widget type
            
            # QLabel styling
            if isinstance(child, QLabel):
                # Check if it's the app title label or app icon (special styling with transparent background)
                if child.text() == "Voice Commander" and child.parent() == self.centralWidget():
                    child.setStyleSheet(f"font-weight: bold; font-size: 16px; {ThemeManager.get_label_style(theme, is_transparent=True)}")
                # Check if it's the app icon
                elif not child.text() and child.pixmap() and child.parent() == self.centralWidget():
                    child.setStyleSheet("background-color: transparent;")
                else:
                    child.setStyleSheet(ThemeManager.get_label_style(theme))
            
            # QComboBox styling
            elif isinstance(child, QComboBox):
                # Ensure selection color contrasts well
                selection_text_color = colors["text_primary"] if theme == "light" else "#ffffff" # Dark text on light accent, White text on dark accent
                child.setStyleSheet(f"""
                    QComboBox {{
                        border: 1px solid {colors["border"]};
                        border-radius: 6px;
                        padding: 5px;
                        background-color: {colors["bg_primary"]}; /* Use primary bg */
                        color: {colors["text_primary"]};
                    }}
                    QComboBox::drop-down {{
                        border: none;
                        width: 24px;
                        /* TODO: Consider styling the dropdown arrow based on theme */
                    }}
                    QComboBox QAbstractItemView {{
                        background-color: {colors["bg_primary"]}; /* Use primary bg */
                        border: 1px solid {colors["border"]};
                        border-radius: 6px;
                        selection-background-color: {colors["bg_accent"]};
                        selection-color: {selection_text_color}; /* Ensure contrast */
                    }}
                """)
            
            # QGroupBox styling
            elif isinstance(child, QGroupBox):
                child.setStyleSheet(f"""
                    QGroupBox {{
                        font-weight: bold;
                        border: 1px solid {colors["border"]};
                        border-radius: 8px;
                        margin-top: 12px;
                        background-color: {colors["bg_primary"]}; /* Use primary bg */
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px;
                        color: {colors["text_primary"]};
                        background-color: {colors["bg_primary"]}; /* Title bg matches GroupBox */
                        border-radius: 4px; /* Optional: Slightly round title bg */
                    }}
                """)
            
            # QTextEdit styling (like status text)
            elif isinstance(child, QTextEdit):
                 # Define selection text color for contrast
                selection_text_color = "#ffffff" if theme == "light" else colors["bg_primary"] # White on light accent, Dark bg color on dark accent
                child.setStyleSheet(f"""
                    border: 1px solid {colors["border"]};
                    border-radius: 8px;
                    background-color: {colors["bg_primary"]}; /* Use primary bg */
                    selection-background-color: {colors["accent"]};
                    selection-color: {selection_text_color}; /* Ensure contrast */
                    color: {colors["text_primary"]};
                """)
            
            # QListWidget styling (chat display)
            elif isinstance(child, QListWidget):
                # Ensure selection color contrasts well
                selection_text_color = colors["text_primary"] if theme == "light" else "#ffffff" # Dark text on light accent, White text on dark accent
                child.setStyleSheet(f"""
                    QListWidget {{
                        border: 1px solid {colors["border"]};
                        border-radius: 8px;
                        background-color: {colors["bg_primary"]}; /* Use primary bg */
                        alternate-background-color: {colors["bg_primary"]}; /* Use primary bg - remove alternation */
                        padding: 2px;
                    }}
                    QListWidget::item {{
                        border-bottom: 1px solid {colors["border"]};
                        padding: 1px;
                        border-radius: 6px; /* Match item widget radius if possible */
                        color: {colors["text_primary"]}; /* Ensure item text color is set */
                        background-color: transparent; /* Ensure item background is transparent by default */
                    }}
                    QListWidget::item:hover {{
                        background-color: {colors["bg_accent"]}; /* Hover uses accent bg */
                    }}
                    QListWidget::item:selected {{
                         background-color: {colors["accent"]}; /* Selection uses main accent */
                         color: {selection_text_color}; /* Ensure contrast for selected text */
                         border-radius: 6px;
                    }}
                """)
            
            # General container QWidget styling
            elif isinstance(child, QWidget) and not isinstance(child, QPushButton):
                # Only style direct container widgets, not those that appear in layouts
                if child.layout() is not None:
                    # This is a container widget with a layout
                    child.setStyleSheet(f"background-color: {colors['bg_primary']};")
            
            # Force update of the widget
            child.style().unpolish(child)
            child.style().polish(child)
            child.update()
    
    def update_transcription_item_themes(self):
        """Update the theme for all transcription items in the chat display"""
        styles = ThemeManager.get_transcription_item_styles(self.theme)
        for i in range(self.chat_display.count()):
            item = self.chat_display.item(i)
            widget = self.chat_display.itemWidget(item)

            # Update TranscriptionListItem widgets
            if hasattr(widget, 'setTheme'):
                widget.setTheme(self.theme) # Assumes setTheme uses styles from ThemeManager
                # Ensure the container widget itself has the correct background
                widget.setStyleSheet(styles["container_style"])

            # Update AI response container widgets (which contain a QLabel)
            elif isinstance(widget, QWidget) and widget.layout():
                # Set the container background first
                widget.setStyleSheet(styles["container_style"])
                for j in range(widget.layout().count()):
                    child = widget.layout().itemAt(j).widget()
                    if isinstance(child, QLabel):
                        # This is an AI response, update its style
                        child.setStyleSheet(styles["ai_response_style"])

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

    def update_ui_state(self):
        """Update UI elements based on current application state"""
        # Define active button style (blue)
        active_button_style = ThemeManager.get_active_button_style(self.theme)
        
        # Inactive button style
        inactive_button_style = ThemeManager.get_inactive_button_style(self.theme)
        
        # Update recording button - only show active when recording
        is_recording = self.transcription_service.is_transcribing
        is_push_to_talk = self.transcription_service.is_push_to_talk_mode
        self.record_button.setText("⏺️ Recording" if is_recording else "⏺️ Start Transcription")
        self.record_button.setStyleSheet(active_button_style if is_recording else inactive_button_style)
        # Disable the record button when push-to-talk is active
        self.record_button.setEnabled(not is_push_to_talk)
        
        # Update push to talk button
        self.push_to_talk_button.setText("🎤 Stop Talking" if is_push_to_talk else "🎤 Push to Talk")
        self.push_to_talk_button.setStyleSheet(active_button_style if is_push_to_talk else inactive_button_style)
        
        # Update mute button
        is_muted = self.groq_service.mute_llm
        self.mute_button.setText(f"🤖 AI Processing: {'Off' if is_muted else 'On'}")
        self.mute_button.setStyleSheet(inactive_button_style if is_muted else active_button_style)
        
        # Update paste button
        is_paste_on = self.groq_service.automatic_paste
        self.paste_button.setText(f"📋 Auto-Paste: {'On' if is_paste_on else 'Off'}")
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
        
        # Save chat history after adding the AI response
        self.save_chat_history()
    
    @pyqtSlot(str)
    def on_error(self, error_msg):
        """Handle error message"""
        self.log_status(f"ERROR: {error_msg}")
    
    @pyqtSlot(bool)
    def on_audio_state_changed(self, is_recording):
        """Handle audio state change"""
        if hasattr(self, 'record_button') and self.record_button is not None:
            self.record_button.setText("Recording" if is_recording else "Start Transcription")
        else:
            logger.warning("record_button not initialized when audio state changed")
        
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
        
    def on_keyboard_error(self, error_msg):
        """Handle keyboard service errors"""
        self.log_status(f"Keyboard error: {error_msg}")
        # Show error in status bar for a short time
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f"Keyboard error: {error_msg}", 5000)
    
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
                
    def load_chat_history(self):
        """Load chat history from disk"""
        try:
            # Get the history save path from config
            save_folder = config.CHAT_HISTORY_SAVE_FOLDER
            
            # Check if the folder exists
            if not os.path.exists(save_folder):
                os.makedirs(save_folder, exist_ok=True)
                self.log_status(f"Created chat history folder: {save_folder}")
                return
                
            # Create history filename
            history_path = os.path.join(save_folder, "chat_history.json")
            
            # Check if the file exists
            if not os.path.exists(history_path):
                self.log_status("No previous chat history found.")
                return
            
            # Verify file is not empty
            if os.path.getsize(history_path) == 0:
                self.log_status("Chat history file exists but is empty.")
                return
                
            # Load the history file
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    chat_history = json.load(f)
                    
                # Verify it's a valid list
                if not isinstance(chat_history, list):
                    self.log_status("Invalid chat history format. Starting new chat.")
                    return
                
                # Proceed only if we have valid history
                if len(chat_history) > 0:
                    # Clear current chat display
                    self.chat_display.clear()
                    
                    # Add each chat item to the display
                    for item in chat_history:
                        if not isinstance(item, dict):
                            continue
                            
                        item_type = item.get('type')
                        if item_type == 'transcription':
                            timestamp = item.get('timestamp', '')
                            text = item.get('text', '')
                            audio_path = item.get('audio_path')
                            
                            # Check if audio file exists
                            if audio_path and not os.path.exists(audio_path):
                                self.log_status(f"Warning: Audio file not found: {audio_path}")
                                audio_path = None
                                
                            # Add transcription item
                            self.add_transcription_item(timestamp, text, audio_path)
                            
                        elif item_type == 'ai_response':
                            text = item.get('text', '')
                            # Add AI response
                            self.add_ai_response(text)
                
                    # Also initialize the groq service chat with history
                    if hasattr(self.groq_service, 'InitializeChat'):
                        self.groq_service.InitializeChat()
                        
                        # Add user messages and assistant messages to the groq service
                        for item in chat_history:
                            if not isinstance(item, dict):
                                continue
                                
                            if item.get('type') == 'transcription':
                                self.groq_service.AddUserMessage(item.get('text', ''))
                            elif item.get('type') == 'ai_response':
                                self.groq_service.AddAssistantMessage(item.get('text', ''))
                
                    # Log success
                    self.log_status(f"Loaded {len(chat_history)} chat messages from history")
            except json.JSONDecodeError:
                self.log_status("Error decoding chat history file. Starting new chat.")
                return
                
        except Exception as e:
            self.log_status(f"Error loading chat history: {e}")
            logger.error(f"Error loading chat history: {e}", exc_info=True)
    
    def save_chat_history(self):
        """Save the current chat history to disk"""
        try:
            # Skip if no chat display exists or it's empty
            if not hasattr(self, 'chat_display') or self.chat_display.count() == 0:
                return
                
            # Get the history save path from config
            save_folder = config.CHAT_HISTORY_SAVE_FOLDER
            # Ensure the folder exists
            os.makedirs(save_folder, exist_ok=True)
            
            # Create history filename
            history_path = os.path.join(save_folder, "chat_history.json")
            
            # Create a list to store chat items
            chat_history = []
            
            # Iterate through all items in chat display
            for i in range(self.chat_display.count()):
                item = self.chat_display.item(i)
                widget = self.chat_display.itemWidget(item)
                
                # Check if it's a transcription item
                if hasattr(widget, 'getText') and callable(widget.getText):
                    # It's a transcription item
                    chat_item = {
                        'type': 'transcription',
                        'timestamp': widget.timestamp if hasattr(widget, 'timestamp') else '',
                        'text': widget.getText(),
                        'audio_path': widget.audio_path if hasattr(widget, 'audio_path') else None
                    }
                    chat_history.append(chat_item)
                    
                # Check if it's an AI response
                elif isinstance(widget, QWidget) and widget.layout():
                    # Look for a QLabel in the widget's layout
                    for j in range(widget.layout().count()):
                        child = widget.layout().itemAt(j).widget()
                        if isinstance(child, QLabel):
                            # Found an AI response label
                            chat_item = {
                                'type': 'ai_response',
                                'text': child.text()
                            }
                            chat_history.append(chat_item)
                            break
            
            # Save to file
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(chat_history, f, ensure_ascii=False, indent=2)
                
            # Log status if verbose
            if config.VERBOSE_OUTPUT:
                self.log_status(f"Saved {len(chat_history)} chat messages to history")
                
        except Exception as e:
            self.log_status(f"Error saving chat history: {e}")
            logger.error(f"Error saving chat history: {e}", exc_info=True)
        
    def copy_to_clipboard(self, text):
        """Copy the given text to clipboard"""
        try:
            pyperclip.copy(text)
            self.log_status(f"Copied to clipboard: {text[:30]}..." if len(text) > 30 else f"Copied to clipboard: {text}")
        except Exception as e:
            self.log_status(f"Error copying to clipboard: {e}")
            
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
                        # Update the item hint based on the widget's recalculated hint
                        list_item.setSizeHint(item_widget.sizeHint())
                        break
                
                self.log_status(f"Re-transcribed audio: {new_text}")
            else:
                self.log_status("Transcription failed")
        except Exception as e:
            self.log_status(f"Error re-transcribing audio: {e}")

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