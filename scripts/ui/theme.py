from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
import os

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
                min-height: 28px;
                max-height: 28px;
                min-width: 28px;
                max-width: 28px;
                color: {colors["text_primary"]};
            }}
            QPushButton:hover {{
                background-color: {colors["inactive_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {colors["inactive_pressed"]};
                min-height: 28px;
                max-height: 28px;
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
        
    @classmethod
    def get_icon_color(cls, theme):
        """Get the appropriate icon color for the current theme"""
        return "#ffffff" if theme.lower() == "dark" else "#000000"
        
    @classmethod
    def get_icon_character(cls, icon_name):
        """Get a simple Unicode character for the specified icon name"""
        icon_map = {
            "record-icon": "⏺",      # Simple record dot
            "mic-icon": "🎙",        # Simple microphone
            "ai-icon": "⚙",          # Simple gear/processing icon
            "paste-icon": "📄",       # Simple document icon
            "new-icon": "⟳",         # Simple refresh/reset icon
            "settings-icon": "⚙",     # Simple gear icon
            "play-icon": "▶",        # Simple triangle play icon
            "stop-icon": "■",        # Simple square stop icon
            "copy-icon": "📄",        # Simple document icon
            "refresh-icon": "⟳",     # Simple refresh icon
            # Default fallback icon
            "default": "•"           # Simple dot as fallback
        }
        
        # Extract base name without path and extension
        if "/" in icon_name:
            icon_name = icon_name.split("/")[-1]
        if "." in icon_name:
            icon_name = icon_name.split(".")[0]
            
        # Return the mapped character or default
        return icon_map.get(icon_name, icon_map["default"])
        
    @classmethod
    def get_themed_icon(cls, icon_path, theme, size=None):
        """
        Instead of loading PNG files which aren't used, just return a simple unicode icon
        """
        # Simple Unicode mapping for common icon names
        icon_map = {
            "assets/play-icon.png": "▶",
            "assets/stop-icon.png": "■",
            "assets/pause-icon.png": "⏸",
            "assets/copy-icon.png": "📄",
            "assets/paste-icon.png": "📋",
            "assets/refresh-icon.png": "⟳",
            "assets/mic-icon.png": "🎤",
            "assets/mute-icon.png": "🔇",
            "assets/settings-icon.png": "⚙",
            "assets/chat-icon.png": "💬",
            "assets/app-icon.png": "🎤",
            "assets/record-icon.png": "⏺",
            "assets/new-icon.png": "🗋",
            "assets/ai-icon.png": "🤖",
        }
        
        # Extract the base filename from the path
        icon_name = icon_path.split("/")[-1] if "/" in icon_path else icon_path
        
        # Create a simple icon with a Unicode character
        icon = QIcon()
        size_value = size if size else 24
        pixmap = QPixmap(size_value, size_value)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Draw the Unicode character on the pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set color based on theme
        if theme.lower() == "dark":
            painter.setPen(QColor("#ffffff"))
        else:
            painter.setPen(QColor("#000000"))
            
        # Get the unicode character
        character = icon_map.get(icon_path, "•")
        
        # Use a font size relative to the icon size
        font_size = max(size_value - 8, 10) if size_value > 16 else size_value - 2
        font = painter.font()
        font.setPointSize(font_size)
        painter.setFont(font)
        
        # Center the text
        rect = QRect(0, 0, size_value, size_value)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, character)
        painter.end()
        
        # Add the pixmap to the icon
        icon.addPixmap(pixmap)
        return icon
    
    @classmethod
    def get_icon_unicode(cls, icon_name):
        """
        Return a simple unicode character for the specified icon name
        """
        # Simple Unicode mapping for common icon names
        icon_map = {
            "play": "▶",
            "stop": "■",
            "pause": "⏸",
            "copy": "📄",
            "paste": "📋",
            "refresh": "⟳",
            "mic": "🎤",
            "mute": "🔇",
            "settings": "⚙",
            "chat": "💬",
            "app": "🎤",
            "new": "🗋",
        }
        
        return icon_map.get(icon_name, "•")
    
    @classmethod
    def get_label_style(cls, theme, is_transparent=False):
        """Get style for labels with option for transparent background"""
        colors = cls.get_theme(theme)
        bg_color = "transparent" if is_transparent else colors["bg_secondary"]
        return f"color: {colors['text_primary']}; background-color: {bg_color};" 