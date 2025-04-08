from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from .theme import ThemeManager

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