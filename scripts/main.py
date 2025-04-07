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
from PyQt6.QtWidgets import QListWidget, QListWidgetItem  # Added for list widget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QMetaObject, QTimer, QPoint, QSettings, QSize
from PyQt6.QtGui import QColor, QTextCursor, QFont, QIcon, QPalette, QAction, QPixmap, QCloseEvent, QPainter, QBrush
from functools import partial  # Added for creating button callbacks
import wave  # Added for reading WAV files
import pygame  # Added for playing audio

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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_path = None
        self.is_playing = False
        self.sound = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components for this widget"""
        # Main layout - horizontal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)  # Slightly increased for better spacing
        main_layout.setSpacing(8)  # Slightly increased for better spacing
        main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Ensure vertical centering
        
        # Timestamp label with better styling
        self.timestamp_label = QLabel()
        self.timestamp_label.setStyleSheet("color: #8892b0; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
        self.timestamp_label.setFixedWidth(80)
        main_layout.addWidget(self.timestamp_label)
        
        # Text content - expand horizontally with better styling
        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("color: #505a7a; font-size: 11pt; font-family: 'Segoe UI', sans-serif;")
        main_layout.addWidget(self.text_label, 1)  # Add stretch factor of 1 to expand
        
        # Button container
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)  # Increased spacing between buttons
        button_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Ensure vertical centering
        
        # Button style
        button_style = """
            QPushButton {
                background-color: #f1f3fa;
                border: none;
                border-radius: 5px;
                padding: 5px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #e1e5ee;
            }
            QPushButton:pressed {
                background-color: #d1d6e6;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:disabled {
                background-color: #f5f7fd;
                color: #a8b3d2;
            }
        """
        
        # Copy button with icon
        self.copy_button = QPushButton()
        self.copy_button.setIcon(QIcon.fromTheme("edit-copy", QIcon("assets/copy-icon.png")))
        self.copy_button.setIconSize(QSize(16, 16))
        self.copy_button.setToolTip("Copy transcription to clipboard")
        self.copy_button.setFixedSize(28, 28)
        self.copy_button.setStyleSheet(button_style)
        button_layout.addWidget(self.copy_button)
        
        # Play button with icon
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start", QIcon("assets/play-icon.png")))
        self.play_button.setIconSize(QSize(16, 16))
        self.play_button.setToolTip("Play audio")
        self.play_button.setFixedSize(28, 28)
        self.play_button.setStyleSheet(button_style)
        self.play_button.setEnabled(False)  # Disabled by default until audio_path is set
        button_layout.addWidget(self.play_button)
        
        # Transcribe Again button with icon
        self.transcribe_button = QPushButton()
        self.transcribe_button.setIcon(QIcon.fromTheme("view-refresh", QIcon("assets/refresh-icon.png")))
        self.transcribe_button.setIconSize(QSize(16, 16))
        self.transcribe_button.setToolTip("Transcribe again")
        self.transcribe_button.setFixedSize(28, 28)
        self.transcribe_button.setStyleSheet(button_style)
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
        
    def setPlaying(self, is_playing):
        """Update the play button state"""
        self.is_playing = is_playing
        if is_playing:
            self.play_button.setIcon(QIcon.fromTheme("media-playback-stop", QIcon("assets/stop-icon.png")))
            self.play_button.setToolTip("Stop playback")
            self.play_button.setStyleSheet("""
                QPushButton {
                    background-color: #f5e7ff;
                    border: none;
                    border-radius: 5px;
                    padding: 5px;
                    min-height: 28px;
                    max-height: 28px;
                }
                QPushButton:hover {
                    background-color: #ead6f5;
                }
                QPushButton:pressed {
                    background-color: #dfc5eb;
                    min-height: 28px;
                    max-height: 28px;
                }
            """)
        else:
            self.play_button.setIcon(QIcon.fromTheme("media-playback-start", QIcon("assets/play-icon.png")))
            self.play_button.setToolTip("Play audio")
            self.play_button.setStyleSheet("""
                QPushButton {
                    background-color: #f1f3fa;
                    border: none;
                    border-radius: 5px;
                    padding: 5px;
                    min-height: 28px;
                    max-height: 28px;
                }
                QPushButton:hover {
                    background-color: #e1e5ee;
                }
                QPushButton:pressed {
                    background-color: #d1d6e6;
                    min-height: 28px;
                    max-height: 28px;
                }
                QPushButton:disabled {
                    background-color: #f5f7fd;
                    color: #a8b3d2;
                }
            """)
        
    def stopPlayback(self):
        """Stop any active playback"""
        if self.sound and self.is_playing:
            self.sound.stop()
            self.setPlaying(False)
            self.sound = None

class VoiceCommanderApp(QMainWindow):
    """
    Main application window for Voice Commander
    """
    # Define some signals
    clear_chat_signal = pyqtSignal()  # Signal to clear chat from any thread
    
    def __init__(self):
        super().__init__()
        
        # Set up the window
        self.setWindowTitle("Voice Commander")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("assets/voice-commander.png"))
        
        # Apply application-wide style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fc;
            }
            QWidget {
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e1e5ee;
                border-radius: 8px;
                margin-top: 12px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #505a7a;
            }
            QLabel {
                color: #505a7a;
            }
            QComboBox {
                border: 1px solid #dee2ec;
                border-radius: 6px;
                padding: 5px;
                background-color: #ffffff;
                color: #505a7a;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #dee2ec;
                border-radius: 6px;
                selection-background-color: #f1f3fa;
                selection-color: #505a7a;
            }
            QScrollBar:vertical {
                border: none;
                background: #f1f3fa;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #cbd2e6;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8b3d2;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #f1f3fa;
                height: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #cbd2e6;
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #a8b3d2;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
            }
            QSplitter::handle {
                background-color: #e1e5ee;
                height: 1px;
            }
            QListWidget {
                border: 1px solid #e1e5ee;
                border-radius: 8px;
                background-color: #ffffff;
                alternate-background-color: #f8f9fc;
            }
            QListWidget::item {
                border-bottom: 1px solid #f1f3fa;
                padding: 3px;
            }
            QListWidget::item:selected {
                background-color: #eef1fa;
                color: #505a7a;
            }
            QTextEdit {
                border: 1px solid #e1e5ee;
                border-radius: 8px;
                background-color: #ffffff;
                selection-background-color: #d7dffa;
                color: #505a7a;
            }
        """)
        
        # Initialize attributes
        self.audio_service = None
        self.vosk_service = None
        self.transcription_service = None
        self.status_text = None
        self.chat_display = None
        self.audio_worker = None
        self.groq_service = None
        self.settings_manager = SettingsManager.SettingsManager()
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
        
        # Initialize keyboard service
        self.keyboard_service = KeyboardService.KeyboardService(self.settings_manager)
        
        # Register shortcut callbacks
        self.keyboard_service.register_shortcut('toggle_push_to_talk', self.toggle_push_to_talk)
        self.keyboard_service.register_shortcut('toggle_recording', self.toggle_recording)
        self.keyboard_service.register_shortcut('toggle_ai_processing', self.toggle_mute)
        self.keyboard_service.register_shortcut('toggle_auto_paste', self.toggle_paste)
        
        # Connect the shortcut_triggered signal
        self.keyboard_service.shortcut_triggered.connect(self.on_shortcut_triggered)
        
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
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)  # Increased margins for better spacing
        main_layout.setSpacing(8)  # Adjusted spacing
        
        # Create a splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(2)  # Thinner splitter handle
        main_layout.addWidget(splitter)
        
        # Chat area
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        # Conversation header with Reset button
        header_layout = QHBoxLayout()
        chat_label = QLabel("Conversation")
        chat_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #505a7a;")
        header_layout.addWidget(chat_label)
        
        # Define button style with modern look
        button_style = """
            QPushButton {
                min-width: 110px;
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
            }
        """
        
        # Push Reset Chat button to the right side
        header_layout.addStretch(1)
        
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
        self.chat_display.setAlternatingRowColors(True)  # Add alternating row colors
        self.chat_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Disable horizontal scrollbar
        self.chat_display.setStyleSheet("""
            QListWidget {
                border: 1px solid #e1e5ee;
                border-radius: 8px;
                background-color: #ffffff;
                alternate-background-color: #f8f9fc;
                padding: 3px;
            }
            QListWidget::item {
                border-bottom: 1px solid #f1f3fa;
                padding: 3px;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background-color: #f5f7fd;
            }
        """)
        self.chat_display.setFont(QFont("Segoe UI", 11))
        self.chat_display.setSpacing(1)  # Reduced spacing between items
        self.chat_display.setWordWrap(True)
        chat_layout.addWidget(self.chat_display)
        
        splitter.addWidget(chat_container)
        
        # Controls area
        controls_container = QWidget()
        controls_container.setStyleSheet("background-color: #f8f9fc;")
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setSpacing(10)  # Increased spacing between group boxes
        controls_layout.setContentsMargins(0, 0, 0, 0)  # Remove container margins
        
        # Group the controls in a grid layout
        controls_group = QGroupBox("Controls")
        controls_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e1e5ee;
                border-radius: 8px;
                margin-top: 12px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #505a7a;
            }
        """)
        controls_grid = QGridLayout()
        controls_grid.setVerticalSpacing(15)
        controls_grid.setHorizontalSpacing(15)
        controls_grid.setContentsMargins(15, 15, 15, 15)  # Increased padding inside group box
        
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
        
        # Row 2: Combined Language and Microphone selection
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
        
        # Add language selection to the combined layout
        selections_layout.addLayout(lang_layout)
        
        # Add some spacing between the selections
        selections_layout.addSpacing(20)
        
        # Microphone selection
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
                
        self.microphone_combo.currentIndexChanged.connect(self.change_microphone)
        mic_layout.addWidget(self.microphone_combo)
        
        # Add microphone selection to the combined layout
        selections_layout.addLayout(mic_layout)
        
        # Add the combined selections to the grid
        controls_grid.addLayout(selections_layout, 1, 0, 1, 3)
        
        # Add a Keyboard Shortcuts section to the settings
        self.setup_shortcut_ui(controls_grid)
        
        # Set the grid layout to the controls group
        controls_group.setLayout(controls_grid)
        controls_layout.addWidget(controls_group)
        
        # Status area
        status_group = QGroupBox("Status")
        status_group.setStyleSheet("QGroupBox { padding-top: 15px; margin-top: 5px; }")
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(10, 5, 10, 5)  # Reduce padding inside group box
        
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
        
        self.log_status("Audio processing initialized. Click 'Start Transcription' to begin recording.")
    
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
        # Use a fixed, smaller height for a leaner look
        item_height = 40  # Increased from 32 to 40 to fix vertical centering
        list_item.setSizeHint(QSize(self.chat_display.width(), item_height))
        
        # Add the widget to the list item
        self.chat_display.addItem(list_item)
        self.chat_display.setItemWidget(list_item, item_widget)
        
        # Scroll to the new item
        self.chat_display.scrollToItem(list_item)
    
    def add_ai_response(self, text):
        """Add an AI response message to the chat display"""
        # Create a container widget for the AI response
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        
        # Create a QLabel for the AI response with better styling
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("""
            color: #505a7a; 
            background-color: #eef1fa; 
            padding: 10px; 
            border-radius: 8px; 
            font-size: 11pt;
            font-family: 'Segoe UI', sans-serif;
        """)
        container_layout.addWidget(label)
        
        # Create a list item and set its size
        list_item = QListWidgetItem(self.chat_display)
        # Adjust for multi-line text - calculate approximate height
        text_lines = max(1, (len(text) // 40) + 1)  # Rough estimate of line count
        item_height = 30 + (text_lines * 20)  # Base height + extra per line
        list_item.setSizeHint(QSize(self.chat_display.width(), item_height))
        
        # Add the widget to the list item
        self.chat_display.addItem(list_item)
        self.chat_display.setItemWidget(list_item, container)
        
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
                self.keyboard_service.stop_listening()
            
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

    def setup_shortcut_ui(self, parent_layout):
        """Set up UI elements for keyboard shortcut configuration"""
        # Create a group box for shortcuts
        shortcuts_group = QGroupBox("Keyboard Shortcuts")
        shortcuts_group.setStyleSheet("QGroupBox { padding-top: 15px; margin-top: 5px; }")
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
            label.setStyleSheet("background: transparent; color: #505a7a;")
            shortcuts_layout.addWidget(label, row, 0)
            
            # Get the current shortcut or "None" if not set
            current_shortcut = self.keyboard_service.get_shortcut(action_name)
            button_text = current_shortcut if current_shortcut else "None"
            
            # Convert to a friendly name for display if it's a virtual key
            if current_shortcut and (current_shortcut.startswith("vk") or current_shortcut.startswith("Key_0x")):
                button_text = self.keyboard_service.get_friendly_key_name(current_shortcut)
            
            # Create button for this shortcut
            shortcut_btn = QPushButton(button_text)
            shortcut_btn.setToolTip("Click to set a new shortcut key (Escape/Delete to clear)")
            shortcut_btn.setMinimumWidth(120)
            
            # Connect button to shortcut recording with the action name
            shortcut_btn.clicked.connect(lambda checked, action=action_name: self.start_shortcut_recording(action))
            
            # Add to layout
            shortcuts_layout.addWidget(shortcut_btn, row, 1)
            
            # Store reference to button for later updates
            self.shortcut_buttons[action_name] = shortcut_btn
        
        # Set the layout for the group box
        shortcuts_group.setLayout(shortcuts_layout)
        
        # Add the group box to the parent layout
        parent_layout.addWidget(shortcuts_group, 4, 0, 1, 3)  # Assuming this goes below existing controls
    
    def start_shortcut_recording(self, action_name):
        """Start recording a new keyboard shortcut for the given action"""
        if action_name not in self.shortcut_buttons:
            return
            
        button = self.shortcut_buttons[action_name]
        
        # Change button text to indicate recording state
        original_text = button.text()
        button.setText("Press any key...")
        button.setStyleSheet("QPushButton { background-color: #ffcccc; }")
        
        # Store the original shortcuts so we can restore them later
        original_shortcuts = {}
        try:
            # Temporarily stop all shortcut listeners while recording
            keyboard.unhook_all_hotkeys()
            logger.debug("Temporarily unhooked all hotkeys for shortcut recording")
        except Exception as e:
            logger.error(f"Error unhooking hotkeys for recording: {e}")
        
        # Flag to track if key was recorded
        key_recorded = False
        
        # Use the keyboard library to record the next keystroke
        def on_key_event(e):
            nonlocal key_recorded
            
            if key_recorded:
                return
                
            try:
                # Mark key as recorded to prevent multiple triggers
                key_recorded = True
                
                # Get the key name from the event
                key_str = e.name
                
                # For modifier combinations, get the full hotkey name
                modifiers = []
                if keyboard.is_pressed('ctrl'):
                    modifiers.append('ctrl')
                if keyboard.is_pressed('alt'):
                    modifiers.append('alt')
                if keyboard.is_pressed('shift'):
                    modifiers.append('shift')
                
                # Build final key string
                if modifiers and key_str not in modifiers:
                    if len(key_str) == 1:  # Single character key
                        key_str = '+'.join(modifiers + [key_str])
                    else:  # Special key
                        key_str = '+'.join(modifiers + [key_str])
                
                # Check if this is a cancel key
                if key_str.lower() in self.keyboard_service.CANCEL_KEYS:
                    # Clear the shortcut
                    self.keyboard_service.set_shortcut(action_name, None)
                    
                    # Update the button text
                    button.setText("None")
                    button.setStyleSheet("")
                    self.log_status(f"Shortcut for {action_name} has been cleared")
                else:
                    # Update the shortcut
                    self.keyboard_service.set_shortcut(action_name, key_str)
                    
                    # Update the button on the main thread
                    button.setText(key_str)
                    button.setStyleSheet("")
                    self.log_status(f"Shortcut for {action_name} set to {key_str}")
            
                # Clean up and unregister the hook
                keyboard.unhook(hook_id)
                
                # Re-register all shortcuts after we're done
                self.keyboard_service._register_all_shortcuts()
                
            except Exception as e:
                logger.error(f"Error in shortcut key handler: {e}")
                button.setText(original_text)
                button.setStyleSheet("")
                # Re-register all shortcuts
                self.keyboard_service._register_all_shortcuts()
        
        # Hook the keyboard event
        hook_id = keyboard.hook(on_key_event)
        
        # Add a timeout to reset the button if no key is pressed
        def reset_button():
            nonlocal key_recorded
            if not key_recorded and button.text() == "Press any key...":
                button.setText(original_text)
                button.setStyleSheet("")
                # Clean up hook if still active
                try:
                    keyboard.unhook(hook_id)
                except:
                    pass
                # Re-register all shortcuts
                self.keyboard_service._register_all_shortcuts()
                
        # Schedule the reset after 5 seconds
        QTimer.singleShot(5000, reset_button)
    
    @pyqtSlot(str)
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
                        text_lines = max(1, (len(new_text) // 40) + 1)
                        item_height = 60 + (text_lines * 20)
                        list_item.setSizeHint(QSize(self.chat_display.width(), item_height))
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
                
                # Only save transcription items, not AI responses
                if isinstance(widget, TranscriptionListItem):
                    chat_history.append({
                        'timestamp': widget.timestamp_label.text().strip(' >'),
                        'text': widget.text_label.text(),
                        'audio_path': widget.audio_path
                    })
            
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
                timestamp = item.get('timestamp', '')
                text = item.get('text', '')
                audio_path = item.get('audio_path')
                
                # Verify audio path exists
                if audio_path and not os.path.exists(audio_path):
                    logger.warning(f"Audio file not found: {audio_path}")
                    audio_path = None
                
                self.add_transcription_item(timestamp, text, audio_path)
            
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