import os
import sys


IS_FROZEN = getattr(sys, "frozen", False)
APP_VERSION = "1.0.0"
GITHUB_REPOSITORY = "AdaelynXIV/ytdlp-gui"
APP_UPDATE_API_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
APP_EXECUTABLE_NAME = "YTDLP-GUI.exe"
UPDATER_EXECUTABLE_NAME = "YTDLP-Updater.exe"
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
FORMAT_OPTIONS = {
    "Best Quality (video + audio)": {"format": "bestvideo+bestaudio/best"},
    "1080p": {"format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]"},
    "720p": {"format": "bestvideo[height<=720]+bestaudio/best[height<=720]"},
    "Audio Only (MP3)": {"audio_only": True},
}


WINDOW_TITLE = "yt-dlp GUI"
WINDOW_SIZE = "700x760"
BG = "#1e1f26"
PANEL = "#2a2c38"
FG = "#f2f2f2"
ACCENT = "#7aa2f7"
MUTED = "#8a8d9f"
CONSOLE_BG = "#14151c"
WARNING = "#f5d90a"
ERROR = "#ff5555"
INFO = "#42d3ec"
