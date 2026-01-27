"""
========================
CONFIGURATION MODULE
========================
This file manages all bot settings and preferences.
Settings are stored in JSON format for persistence.
"""

import json
import os
from typing import Optional

# ========================
# SETTINGS FILE PATH
# ========================
# All bot settings are saved here so they persist after restart
SETTINGS_FILE = "bot_settings.json"

# ========================
# DEFAULT SETTINGS
# ========================
# These are the initial settings when bot starts for the first time
DEFAULT_SETTINGS = {
    "protection_enabled": False,      # Bot starts in OFF mode for safety
    "clip_path": None,                # Path to the protection clip video
    "position": "start",              # Where to insert clip: start/middle/end/random
    "audio_mode": "mix",              # How to handle audio: mix/clip/original
    "clip_duration": 0,               # Duration of protection clip in seconds
}


class Config:
    """
    Configuration manager class.
    Handles loading, saving, and updating bot settings.
    """
    
    def __init__(self):
        """
        Initialize configuration.
        Load existing settings or create default ones.
        """
        self.settings = self.load_settings()
    
    def load_settings(self) -> dict:
        """
        Load settings from JSON file.
        If file doesn't exist, create it with default settings.
        
        Returns:
            dict: Current bot settings
        """
        # Check if settings file exists
        if os.path.exists(SETTINGS_FILE):
            try:
                # Try to read and parse the JSON file
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                print(f"✓ Loaded settings from {SETTINGS_FILE}")
                return settings
            except Exception as e:
                # If file is corrupted, use defaults
                print(f"⚠ Error loading settings: {e}")
                print("Using default settings...")
                return DEFAULT_SETTINGS.copy()
        else:
            # No settings file exists, create one with defaults
            print(f"Creating new settings file: {SETTINGS_FILE}")
            self.save_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS.copy()
    
    def save_settings(self, settings: dict = None):
        """
        Save settings to JSON file.
        
        Args:
            settings: Settings dictionary to save (uses self.settings if None)
        """
        if settings is None:
            settings = self.settings
        
        try:
            # Write settings to file with nice formatting
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
            print(f"✓ Settings saved to {SETTINGS_FILE}")
        except Exception as e:
            print(f"✗ Error saving settings: {e}")
    
    def get(self, key: str, default=None):
        """
        Get a specific setting value.
        
        Args:
            key: Setting name
            default: Default value if key doesn't exist
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def set(self, key: str, value):
        """
        Update a setting and save to file.
        
        Args:
            key: Setting name
            value: New value
        """
        self.settings[key] = value
        self.save_settings()
    
    def get_status_text(self) -> str:
        """
        Generate a formatted status message showing all current settings.
        
        Returns:
            str: Formatted status message
        """
        status = "📊 **Current Bot Status**\n\n"
        
        # Protection mode status
        if self.get("protection_enabled"):
            status += "🟢 **Protection Mode:** ENABLED\n"
        else:
            status += "🔴 **Protection Mode:** DISABLED\n"
        
        status += "\n**Settings:**\n"
        
        # Clip information
        clip_path = self.get("clip_path")
        if clip_path and os.path.exists(clip_path):
            duration = self.get("clip_duration", 0)
            status += f"✓ Protection Clip: Set ({duration:.1f}s)\n"
        else:
            status += "✗ Protection Clip: Not set\n"
        
        # Position setting
        position = self.get("position", "start")
        status += f"📍 Insertion Position: {position}\n"
        
        # Audio mode
        audio_mode = self.get("audio_mode", "mix")
        status += f"🔊 Audio Mode: {audio_mode}\n"
        
        # Instructions
        status += "\n**Available Commands:**\n"
        status += "/setclip - Upload protection clip\n"
        status += "/setposition - Set clip position\n"
        status += "/setaudio - Set audio mode\n"
        status += "/on - Enable protection\n"
        status += "/off - Disable protection\n"
        status += "/status - Show this status\n"
        
        return status


# ========================
# GLOBAL CONFIG INSTANCE
# ========================
# Create a single config instance to be used throughout the bot
config = Config()
