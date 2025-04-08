from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from .theme import ThemeManager

class TranscriptionListItem(QWidget):
    """Custom widget for displaying a transcription item in the list"""
    
    def __init__(self, parent=None, theme="dark", is_ai=False):
        super().__init__(parent)
        self.audio_path = None
        self.is_playing = False
        self.sound = None
        self.theme = theme
        self.is_ai = is_ai
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components for this widget"""
        # Get theme styles
        styles = ThemeManager.get_transcription_item_styles(self.theme)
        # Set container background
        self.setStyleSheet(styles["container_style"])
        
        # Main layout - horizontal with gradient background
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 1, 4, 1)  # Reduced margins
        main_layout.setSpacing(4) # Reduced spacing
        main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Timestamp label with better styling
        self.timestamp_label = QLabel()
        self.timestamp_label.setStyleSheet(styles["timestamp_style"])
        self.timestamp_label.setFixedWidth(80)
        main_layout.addWidget(self.timestamp_label)
        
        # Text content - expand horizontally using user bubble style
        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        bubble_style = styles["ai_response_style"] if self.is_ai else styles["user_bubble_style"]
        self.text_label.setStyleSheet(bubble_style)
        self.text_label.setMinimumHeight(16)
        # Set size policy to encourage vertical expansion for wrapped text
        self.text_label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding))
        main_layout.addWidget(self.text_label, 1)  # Add stretch factor of 1 to expand
        
        # Button container
        button_layout = QHBoxLayout()
        button_layout.setSpacing(2) # Reduced spacing
        button_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Copy button with simple Unicode icon
        self.copy_button = QPushButton()
        self.copy_button.setText("📄")  # Simple document icon
        self.copy_button.setToolTip("Copy transcription to clipboard")
        self.copy_button.setFixedSize(24, 24)  # Reduced size
        self.copy_button.setStyleSheet(styles["button_style"]) # Style already updated by Jill's change
        button_layout.addWidget(self.copy_button)
        
        # Play button with simple Unicode icon
        self.play_button = QPushButton()
        self.play_button.setText("▶")  # Simple triangle play icon
        self.play_button.setToolTip("Play audio")
        self.play_button.setFixedSize(24, 24)  # Reduced size
        self.play_button.setStyleSheet(styles["button_style"]) # Style already updated by Jill's change
        self.play_button.setEnabled(False)  # Disabled by default until audio_path is set
        button_layout.addWidget(self.play_button)
        
        # Transcribe Again button with simple Unicode icon
        self.transcribe_button = QPushButton()
        self.transcribe_button.setText("⟳")  # Simple refresh icon
        self.transcribe_button.setToolTip("Transcribe again")
        self.transcribe_button.setFixedSize(24, 24)  # Reduced size
        self.transcribe_button.setStyleSheet(styles["button_style"]) # Style already updated by Jill's change
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
        self.timestamp = timestamp
        
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
        """Update the widget with the current theme"""
        self.theme = theme
        styles = ThemeManager.get_transcription_item_styles(theme)
        colors = ThemeManager.get_theme(theme)

        # Update container background
        self.setStyleSheet(styles["container_style"])

        # Update timestamp and text bubble
        self.timestamp_label.setStyleSheet(styles["timestamp_style"])
        bubble_style = styles["ai_response_style"] if self.is_ai else styles["user_bubble_style"]
        self.text_label.setStyleSheet(bubble_style)

        # Update buttons (inactive state)
        inactive_style = styles["button_style"]
        self.copy_button.setStyleSheet(inactive_style)
        self.transcribe_button.setStyleSheet(inactive_style)

        # Update play/stop button based on current state
        self.setPlaying(self.is_playing)

    def setPlaying(self, is_playing):
        """Update the play button state and style"""
        self.is_playing = is_playing
        styles = ThemeManager.get_transcription_item_styles(self.theme)
        colors = ThemeManager.get_theme(self.theme)

        if is_playing:
            # Define active style using accent color
            text_color = "#ffffff" if self.theme == "light" else colors["bg_primary"] # Contrast text
            active_style = f"""
                QPushButton {{
                    background-color: {colors["accent"]};
                    border: 1px solid {colors["accent"]};
                    color: {text_color};
                    border-radius: 4px;
                    padding: 1px; /* Match reduced padding */
                    min-height: 24px; /* Reduced size */
                    max-height: 24px;
                    min-width: 24px;
                    max-width: 24px;
                    font-size: 14pt; /* Larger icon size */
                }}
                QPushButton:hover {{
                     background-color: {ThemeManager._adjust_color(colors["accent"], -20 if self.theme == 'light' else 20)};
                     border-color: {ThemeManager._adjust_color(colors["accent"], -20 if self.theme == 'light' else 20)};
                }}
                QPushButton:pressed {{
                     background-color: {ThemeManager._adjust_color(colors["accent"], -40 if self.theme == 'light' else 40)};
                     border-color: {ThemeManager._adjust_color(colors["accent"], -40 if self.theme == 'light' else 40)};
                }}
            """
            self.play_button.setText("■")  # Simple square stop icon
            self.play_button.setToolTip("Stop playback")
            self.play_button.setStyleSheet(active_style)
        else:
            # Revert to standard small button style (already includes larger font size from Jill's change)
            self.play_button.setText("▶")  # Simple triangle play icon
            self.play_button.setToolTip("Play audio")
            self.play_button.setStyleSheet(styles["button_style"]) # Uses updated small button style from ThemeManager
        
    def stopPlayback(self):
        """Stop any active playback"""
        if self.sound and self.is_playing:
            self.sound.stop()
            self.setPlaying(False)
            self.sound = None 