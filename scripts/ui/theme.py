from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
import os

class ThemeManager:
    """Manages application themes and provides styling"""
    
    # Light theme colors (Clean & Professional)
    LIGHT_THEME = {
        "bg_primary": "#ffffff",      # White
        "bg_secondary": "#ffffff",      # White (kept for compatibility, but ideally unused)
        "bg_accent": "#f0f0f0",       # Very light grey (hover/selection)
        "text_primary": "#212121",     # Dark grey
        "text_secondary": "#757575",     # Medium grey
        "border": "#bdbdbd",       # Medium grey
        "accent": "#007bff",       # Standard blue
        "success": "#10b981",       # Keep functional colors
        "warning": "#f59e0b",
        "error": "#ef4444",
        "scrollbar": "#f0f0f0",       # Light scrollbar
        "scrollbar_handle": "#bdbdbd", # Medium grey handle
        "scrollbar_handle_hover": "#a0a0a0" # Darker grey handle hover
    }
    
    # Dark theme colors (Dark Cyan Tint)
    DARK_THEME = {
        "bg_primary": "#0a192f",      # Very dark navy/slate
        "bg_secondary": "#0a192f",      # Same as primary (kept for compatibility)
        "bg_accent": "#172a45",       # Slightly lighter shade (hover/selection)
        "text_primary": "#ccd6f6",     # Light grey/blue
        "text_secondary": "#8892b0",     # Slightly dimmer text
        "border": "#303C55",       # Subtle border
        "accent": "#64ffda",       # Bright cyan/aqua
        "success": "#2cb67d",       # Keep functional colors
        "warning": "#ff8906",
        "error": "#f25042",
        "scrollbar": "#172a45",       # Darker scrollbar bg
        "scrollbar_handle": "#303C55", # Subtle handle
        "scrollbar_handle_hover": "#506680" # Lighter handle hover
    }
    
    @classmethod
    def get_theme(cls, theme_name="light"):
        """Get theme colors dictionary"""
        return cls.DARK_THEME if theme_name.lower() == "dark" else cls.LIGHT_THEME
    
    @classmethod
    def get_main_window_style(cls, theme):
        """Get stylesheet for main window and base elements"""
        colors = cls.get_theme(theme)
        # Simplified: Only set main window background, base font, default text color, scrollbars, splitter
        return f"""
            QMainWindow {{
                background-color: {colors["bg_primary"]};
            }}
            QWidget {{
                font-family: 'Segoe UI', sans-serif;
                color: {colors["text_primary"]}; /* Default text color */
                background-color: transparent; /* Default background */
            }}
            /* Keep Scrollbar styles */
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
            /* Keep Splitter style */
            QSplitter::handle {{
                background-color: {colors["border"]};
                height: 1px; /* Make thinner */
                width: 1px; /* Make thinner */
            }}
            /* Styles for QGroupBox, QLabel, QComboBox, QListWidget, QTextEdit are now primarily handled in app.py apply_theme_to_all_widgets */
        """
    
    @classmethod
    def get_active_button_style(cls, theme):
        """Get active button style"""
        colors = cls.get_theme(theme)
        # Define text color based on theme for contrast with accent
        text_color = "#ffffff" if theme == "light" else colors["bg_primary"] # White on light blue, Dark bg color on dark cyan
        return f"""
            QPushButton {{
                min-width: 110px;
                min-height: 24px;
                max-height: 24px;
                padding: 8px;
                border-radius: 6px;
                border: 1px solid {colors["accent"]}; /* Use accent color for border */
                background-color: {colors["accent"]};
                color: {text_color};
                font-weight: 600;
            }}
            QPushButton:hover {{
                /* Slightly darken/lighten accent for hover - simple approach */
                background-color: {cls._adjust_color(colors["accent"], -20 if theme == 'light' else 20)};
                border-color: {cls._adjust_color(colors["accent"], -20 if theme == 'light' else 20)};
            }}
            QPushButton:pressed {{
                background-color: {cls._adjust_color(colors["accent"], -40 if theme == 'light' else 40)};
                border-color: {cls._adjust_color(colors["accent"], -40 if theme == 'light' else 40)};
                min-height: 24px; /* Keep size consistent */
                max-height: 24px;
            }}
            QPushButton:disabled {{
                background-color: {colors["bg_accent"]}; /* Use accent bg for disabled */
                border-color: {colors["border"]};
                color: {colors["text_secondary"]};
            }}
        """
    
    @classmethod
    def get_inactive_button_style(cls, theme):
        """Get inactive button style"""
        colors = cls.get_theme(theme)
        # Use bg_accent for light inactive, a specific darker shade for dark inactive
        inactive_bg = colors["bg_accent"] if theme == "light" else "#172a45" # Light: bg_accent, Dark: specific shade
        inactive_hover_bg = cls._adjust_color(inactive_bg, -10 if theme == 'light' else 10)
        inactive_pressed_bg = cls._adjust_color(inactive_bg, -20 if theme == 'light' else 20)

        return f"""
            QPushButton {{
                min-width: 110px;
                min-height: 24px;
                max-height: 24px;
                padding: 8px;
                border-radius: 6px;
                border: 1px solid {colors["border"]}; /* Use standard border */
                background-color: {inactive_bg};
                color: {colors["text_primary"]};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {inactive_hover_bg};
                border-color: {cls._adjust_color(colors["border"], 0 if theme == 'light' else 15)}; /* Slightly lighter border on dark hover */
            }}
            QPushButton:pressed {{
                background-color: {inactive_pressed_bg};
                border-color: {cls._adjust_color(colors["border"], 0 if theme == 'light' else 25)};
                min-height: 24px; /* Keep size consistent */
                max-height: 24px;
            }}
            QPushButton:disabled {{
                background-color: {colors["bg_accent"]}; /* Use accent bg for disabled */
                border-color: {colors["border"]};
                color: {colors["text_secondary"]};
                opacity: 0.7; /* Make it look more disabled */
            }}
        """
    
    @classmethod
    def get_small_button_style(cls, theme):
        """Get style for small buttons"""
        colors = cls.get_theme(theme)
        # Use bg_accent for base background, consistent with inactive elements
        small_button_bg = colors["bg_accent"]
        small_hover_bg = cls._adjust_color(small_button_bg, -10 if theme == 'light' else 10)
        small_pressed_bg = cls._adjust_color(small_button_bg, -20 if theme == 'light' else 20)

        return f"""
            QPushButton {{
                background-color: {small_button_bg};
                border: 1px solid {colors["border"]}; /* Add border */
                border-radius: 4px;
                padding: 1px; /* Reduced padding */
                min-height: 24px; /* Reduced size */
                max-height: 24px; /* Reduced size */
                min-width: 24px; /* Reduced size */
                max-width: 24px; /* Reduced size */
                color: {colors["text_primary"]};
                /* TODO: Consider adding icon color setting if needed */
            }}
            QPushButton:hover {{
                background-color: {small_hover_bg};
                border-color: {cls._adjust_color(colors["border"], 0 if theme == 'light' else 15)}; /* Match inactive button hover */
            }}
            QPushButton:pressed {{
                background-color: {small_pressed_bg};
                border-color: {cls._adjust_color(colors["border"], 0 if theme == 'light' else 25)}; /* Match inactive button pressed */
                min-height: 24px; /* Keep reduced size consistent */
                max-height: 24px;
            }}
            QPushButton:disabled {{
                background-color: {cls._adjust_color(small_button_bg, -5 if theme == 'light' else 5)}; /* Slightly adjusted bg */
                border-color: {cls._adjust_color(colors["border"], -10 if theme == 'light' else -5)}; /* Dimmer border */
                color: {colors["text_secondary"]};
                opacity: 0.6; /* Slightly more opacity */
            }}
        """
    
    @classmethod
    def get_dialog_style(cls, theme):
        """Get dialog style consistent with main theme"""
        colors = cls.get_theme(theme)
        # Define selection text color for contrast within dialog inputs
        selection_text_color_input = "#ffffff" if theme == "light" else colors["bg_primary"] # White on light accent, Dark bg color on dark accent

        return f"""
            QDialog {{
                background-color: {colors["bg_primary"]};
                color: {colors["text_primary"]}; /* Ensure default text color */
            }}
            /* Apply consistent GroupBox style */
            /* QGroupBox styling removed as it's overridden in SettingsDialog.apply_theme */
            /* Apply consistent LineEdit style */
            /* QLineEdit styling removed as it's overridden in SettingsDialog.apply_theme */
            /* Apply consistent TextEdit style */
            /* QTextEdit styling removed as it's overridden in SettingsDialog.apply_theme */
            /* Add default Label style for dialogs */
            /* QLabel styling removed as it's overridden in SettingsDialog.apply_theme */
            /* Style buttons within dialogs consistently */
            /* QPushButton styling removed as it's overridden in SettingsDialog.apply_theme */
        """
    
    @classmethod
    def get_transcription_item_styles(cls, theme):
        """Get styles for transcription list items"""
        colors = cls.get_theme(theme)
        # User bubble: Transparent background, no border, minimal padding
        user_bubble_style = f"""
            QLabel {{
                color: {colors["text_primary"]};
                background-color: transparent; /* Transparent */
                padding: 1px; /* Minimal padding */
                border: none; /* No border */
                /* border-radius removed */
                font-size: 11pt;
                font-family: 'Segoe UI', sans-serif;
                margin: 2px; /* Keep slight margin */
            }}
        """
        # AI response: Transparent background, no border, minimal padding
        ai_response_style = f"""
            QLabel {{
                color: {colors["text_primary"]};
                background-color: transparent; /* Transparent */
                padding: 1px; /* Minimal padding */
                border: none; /* No border */
                /* border-radius removed */
                font-size: 11pt;
                font-family: 'Segoe UI', sans-serif;
                margin: 2px; /* Keep slight margin */
            }}
        """

        return {
            "user_bubble_style": user_bubble_style,
            "ai_response_style": ai_response_style,
            "timestamp_style": f"color: {colors['text_secondary']}; font-size: 9pt;",
            "container_style": f"background-color: {colors['bg_primary']}; border: none;", # Container for item widget should blend in
            "button_style": cls.get_small_button_style(theme) # Use existing small style for consistency
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
    def get_label_style(cls, theme, is_transparent=False):
        """Get default label style"""
        colors = cls.get_theme(theme)
        bg_color = "transparent" if is_transparent else colors['bg_primary']
        return f"color: {colors['text_primary']}; background-color: {bg_color};"

    # Helper method to adjust color brightness (simple version)
    # Might need a more robust implementation if complex adjustments are needed
    @classmethod
    def _adjust_color(cls, hex_color, amount):
        """Lighten or darken a hex color"""
        try:
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            new_rgb = tuple(max(0, min(255, c + amount)) for c in rgb)
            return f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"
        except:
            return hex_color # Return original if adjustment fails 