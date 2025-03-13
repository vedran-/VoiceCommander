import sys
import os
import logging
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtWidgets import QTextEdit, QLabel, QComboBox, QSplitter, QGroupBox, QGridLayout, QScrollArea
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QMetaObject
from PyQt6.QtGui import QColor, QTextCursor, QFont, QIcon

# Import our services
from . import dependencies
from . import VoskService
from . import AudioService
from . import TranscriptionService
from . import SettingsManager
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
        self.setWindowIcon(QIcon("assets/icon.ico"))
        
        # Initialize attributes
        self.audio_service = None
        self.vosk_service = None
        self.transcription_service = None
        self.status_text = None
        self.chat_display = None
        self.audio_worker = None
        self.groq_service = None
        self.settings_manager = SettingsManager.SettingsManager()
        
        # Connect signals
        self.clear_chat_signal.connect(self._clear_chat_display)
        
        # Initialize status_text for early logging
        self.status_text = None
        
        # Initialize services first
        self.initialize_services()
        
        # Build UI after services are initialized
        self.setup_ui()
        
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
        
        # Set language from settings
        saved_language = self.settings_manager.get('language', 'en')
        self.groq_service.language = saved_language
        
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
        
        # Create a splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Chat area
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        
        chat_label = QLabel("Conversation")
        chat_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        chat_layout.addWidget(chat_label)
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #f0f0f0;")
        self.chat_display.setFont(QFont("Segoe UI", 11))
        chat_layout.addWidget(self.chat_display)
        
        splitter.addWidget(chat_container)
        
        # Controls area
        controls_container = QWidget()
        controls_layout = QVBoxLayout(controls_container)
        
        # Group the controls in a grid layout
        controls_group = QGroupBox("Controls")
        controls_grid = QGridLayout()
        
        # Row 1: Transcription controls
        self.record_button = QPushButton("Stop Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        controls_grid.addWidget(self.record_button, 0, 0)
        
        self.mute_button = QPushButton("Unmute LLM")
        self.mute_button.clicked.connect(self.toggle_mute)
        controls_grid.addWidget(self.mute_button, 0, 1)
        
        self.paste_button = QPushButton("Disable Paste")
        self.paste_button.clicked.connect(self.toggle_paste)
        controls_grid.addWidget(self.paste_button, 0, 2)
        
        # Row 2: Language and Reset controls
        self.reset_button = QPushButton("Reset Chat")
        self.reset_button.clicked.connect(self.reset_chat)
        controls_grid.addWidget(self.reset_button, 1, 0)
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        
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
        
        lang_widget = QWidget()
        lang_widget.setLayout(lang_layout)
        controls_grid.addWidget(lang_widget, 1, 1, 1, 2)
        
        # Row 3: Microphone selection
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
        
        mic_refresh_button = QPushButton("Refresh")
        mic_refresh_button.clicked.connect(self.refresh_microphones)
        mic_layout.addWidget(mic_refresh_button)
        
        mic_widget = QWidget()
        mic_widget.setLayout(mic_layout)
        controls_grid.addWidget(mic_widget, 2, 0, 1, 3)
        
        # Set the grid layout to the controls group
        controls_group.setLayout(controls_grid)
        controls_layout.addWidget(controls_group)
        
        # Status area
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
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
    
    def refresh_microphones(self):
        """Refresh the list of available microphones"""
        # Get fresh list of devices
        self.audio_service.device_list = self.audio_service.get_input_devices_list()
        
        # Update the UI
        self.populate_microphones()
        
        # Try to select the current device
        current_device = self.audio_service.device_index
        for i in range(self.microphone_combo.count()):
            if self.microphone_combo.itemData(i) == current_device:
                self.microphone_combo.setCurrentIndex(i)
                break
    
    def update_ui_state(self):
        """Update UI elements based on current application state"""
        # Update recording button
        is_recording = self.transcription_service.is_transcribing
        self.record_button.setText("Stop Recording" if is_recording else "Start Recording")
        
        # Update mute button
        is_muted = self.groq_service.mute_llm
        self.mute_button.setText("Unmute LLM" if is_muted else "Mute LLM")
        
        # Update paste button
        is_paste_on = self.groq_service.automatic_paste
        self.paste_button.setText("Disable Paste" if is_paste_on else "Enable Paste")
    
    def start_audio_processing(self):
        """Start the audio processing thread"""
        # Start the transcription service
        self.transcription_service.start_transcription()
        
        # Create and start the audio processing worker
        self.audio_worker = AudioProcessingWorker(self.transcription_service)
        self.audio_worker.start()
        
        self.log_status("Audio processing started")
    
    # Signal handlers
    @pyqtSlot(str)
    def on_transcription_result(self, text):
        """Handle new transcription result"""
        self.add_chat_message(text, is_user=True)
    
    @pyqtSlot(str)
    def on_llm_response(self, text):
        """Handle LLM response"""
        self.add_chat_message(text, is_user=False)
    
    @pyqtSlot(str)
    def on_error(self, error_msg):
        """Handle error message"""
        self.log_status(f"ERROR: {error_msg}")
    
    @pyqtSlot(bool)
    def on_audio_state_changed(self, is_recording):
        """Handle audio state change"""
        self.record_button.setText("Stop Recording" if is_recording else "Start Recording")
    
    def add_chat_message(self, text, is_user=True):
        """Add a message to the chat display"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Format based on message type
        if is_user:
            # Format: timestamp > user_message
            formatted_text = f"<span style='color:#c2a000;'>{text}</span>"
        else:
            # Format: AI response
            formatted_text = f"<span style='color:#0078d7;'>{text}</span>"
        
        cursor.insertHtml(formatted_text)
        cursor.insertHtml("<br>")
        
        # Scroll to bottom
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()
    
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
        if self.transcription_service.is_transcribing:
            self.transcription_service.pause_transcription()
        else:
            self.transcription_service.resume_transcription()
    
    def toggle_mute(self):
        """Toggle LLM mute state"""
        self.groq_service.mute_llm = not self.groq_service.mute_llm
        status = "muted" if self.groq_service.mute_llm else "unmuted"
        self.log_status(f"AI chat {status}")
        
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
        
        # Only attempt TTS if not muted
        if not self.groq_service.mute_llm:
            try:
                self.groq_service.safe_tts_say(f"Automatic paste {status}")
            except Exception as e:
                self.log_status(f"TTS error: {e}")
        
        self.update_ui_state()
    
    def reset_chat(self):
        """Reset the chat history"""
        try:
            # Reset the chat history in the service
            self.groq_service.InitializeChat()
            self.log_status("Chat history reset")
            
            # Emit signal to clear chat display in the UI thread
            self.clear_chat_signal.emit()
            
            # Only attempt TTS if not muted
            if not self.groq_service.mute_llm:
                try:
                    self.groq_service.safe_tts_say("Chat history reset")
                except Exception as e:
                    self.log_status(f"TTS error: {e}")
        except Exception as e:
            self.log_status(f"Error resetting chat: {e}")
            logger.error(f"Error in reset_chat: {e}", exc_info=True)
    
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
        # Save window position and size
        self.settings_manager.set('window_position', [self.x(), self.y()])
        self.settings_manager.set('window_size', [self.width(), self.height()])
        
        # Stop the audio worker
        if hasattr(self, 'audio_worker'):
            self.audio_worker.stop()
        
        # Stop the transcription service
        if hasattr(self, 'transcription_service'):
            self.transcription_service.stop_transcription()
        
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