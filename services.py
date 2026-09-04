import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading

import imageio_ffmpeg
import requests
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

from packaging.version import parse as parse_version

from config import (
    APP_EXECUTABLE_NAME,
    APP_UPDATE_API_URL,
    APP_VERSION,
    FORMAT_OPTIONS,
    IS_FROZEN,
    UPDATER_EXECUTABLE_NAME,
)


def github_headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def progress_hook(message_queue, data):
    if data["status"] == "downloading":
        percent_text = data.get("_percent_str", "0.0%").strip().replace("%", "")
        try:
            percent = float(percent_text)
        except ValueError:
            percent = 0.0
        speed = data.get("_speed_str", "").strip()
        message_queue.put(
            ("progress", percent, f"Downloading... {percent:.1f}% at ({speed})")
        )
    elif data["status"] == "finished":
        message_queue.put(("progress", 100, "Merging / Finishing up..."))


class QueueLogger:
    def __init__(self, message_queue):
        self.message_queue = message_queue

    def debug(self, message):
        self.message_queue.put(("log", message, "normal"))

    def warning(self, message):
        self.message_queue.put(("log", f"WARNING: {message}", "warning"))

    def error(self, message):
        self.message_queue.put(("log", f"ERROR: {message}", "error"))


def run_download(url, format_name, output_dir, message_queue):
    options = FORMAT_OPTIONS[format_name]
    ydl_options = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [lambda data: progress_hook(message_queue, data)],
        "logger": QueueLogger(message_queue),
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "impersonate": ImpersonateTarget(client="chrome"),
    }

    if options.get("audio_only"):
        ydl_options["format"] = "bestaudio/best"
        ydl_options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }]
    else:
        ydl_options["format"] = options["format"]
        ydl_options["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_options) as downloader:
            downloader.download([url])
        message_queue.put(("done", 0))
    except Exception as error:
        message_queue.put(("log", f"ERROR: {error}", "error"))
        message_queue.put(("done", 1))


def get_pip_command():
    if not IS_FROZEN:
        import sys

        return [sys.executable, "-m", "pip"]

    for executable in ("py", "python", "python3"):
        python_executable = shutil.which(executable)
        if python_executable:
            return [python_executable, "-m", "pip"]
    return None


def run_update(message_queue):
    message_queue.put(("log", "--- Checking for updates ---", "info"))
    try:
        pip_command = get_pip_command()
        if pip_command is None:
            raise RuntimeError("No Python installation was found to run pip")

        result = subprocess.run(
            pip_command + [
                "install",
                "--upgrade",
                "yt-dlp",
                "curl-cffi",
                "imageio-ffmpeg",
            ],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            message_queue.put(("log", line, "info"))

        if result.returncode == 0:
            if IS_FROZEN:
                message_queue.put(
                    ("log", "Packages updated. Rebuild the .exe to include the new versions.", "info")
                )
            else:
                message_queue.put(("log", "yt-dlp and ffmpeg are up to date.", "info"))
            threading.Thread(
                target=check_versions, args=(message_queue,), daemon=True
            ).start()
            threading.Thread(
                target=check_ffmpeg_versions, args=(message_queue,), daemon=True
            ).start()
        else:
            for line in result.stderr.splitlines():
                message_queue.put(("log", line, "error"))
            message_queue.put(("log", "Update failed.", "error"))
    except Exception as error:
        message_queue.put(("log", f"Update error: {error}", "error"))
    message_queue.put(("update_done", None))


def check_versions(message_queue):
    installed = yt_dlp.version.__version__
    latest = None
    try:
        response = requests.get(
            "https://pypi.org/pypi/yt-dlp/json",
            timeout=10,
            headers={"User-Agent": "ytdlp-gui/1.0"},
        )
        response.raise_for_status()
        latest = response.json()["info"]["version"]
    except Exception as error:
        message_queue.put(("log", f"Version check failed: {error}", "warning"))

    message_queue.put(("version", installed, latest))


def check_ffmpeg_versions(message_queue):
    try:
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        first_line = result.stdout.splitlines()[0]
        match = re.search(r"ffmpeg version\s+(\S+)", first_line)
        binary_version = match.group(1) if match else "unknown"
        installed_package = imageio_ffmpeg.__version__
        latest_package = None
        response = requests.get(
            "https://pypi.org/pypi/imageio-ffmpeg/json",
            timeout=10,
            headers={"User-Agent": "ytdlp-gui/1.0"},
        )
        response.raise_for_status()
        latest_package = response.json()["info"]["version"]
        message_queue.put(
            ("ffmpeg_version", binary_version, installed_package, latest_package)
        )
    except Exception as error:
        message_queue.put(("ffmpeg_version_error", str(error)))


def check_app_update(message_queue):
    try:
        response = requests.get(
            APP_UPDATE_API_URL,
            timeout=10,
            headers=github_headers(),
        )
        response.raise_for_status()
        release = response.json()
        latest = release["tag_name"].lstrip("v")
        if parse_version(latest) <= parse_version(APP_VERSION):
            message_queue.put(("app_update_current", latest))
            return

        asset = next(
            (item for item in release.get("assets", []) if item["name"] == APP_EXECUTABLE_NAME),
            None,
        )
        updater_asset = next(
            (item for item in release.get("assets", []) if item["name"] == UPDATER_EXECUTABLE_NAME),
            None,
        )
        if asset is None or updater_asset is None:
            raise RuntimeError(
                f"Release {latest} must include {APP_EXECUTABLE_NAME} and {UPDATER_EXECUTABLE_NAME}"
            )
        message_queue.put(
            (
                "app_update_available",
                latest,
                asset["browser_download_url"],
                updater_asset["browser_download_url"],
            )
        )
    except Exception as error:
        message_queue.put(("app_update_error", str(error)))


def download_app_update(download_url, updater_download_url, message_queue):
    if not IS_FROZEN:
        message_queue.put(("app_update_error", "Application updates require the built .exe"))
        return

    update_path = None
    updater_update_path = None
    try:
        for download_url, suffix in (
            (download_url, "-app.exe"),
            (updater_download_url, "-updater.exe"),
        ):
            response = requests.get(
                download_url,
                stream=True,
                timeout=30,
                headers=github_headers(),
            )
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(
                prefix="ytdlp-gui-", suffix=suffix, delete=False
            ) as update_file:
                if suffix == "-app.exe":
                    update_path = update_file.name
                else:
                    updater_update_path = update_file.name
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        update_file.write(chunk)

        application_path = os.path.abspath(sys.executable)
        updater_path = os.path.join(
            os.path.dirname(application_path), UPDATER_EXECUTABLE_NAME
        )
        if not os.path.exists(updater_path):
            raise RuntimeError(f"Missing {UPDATER_EXECUTABLE_NAME} next to the application")

        os.replace(updater_update_path, updater_path)
        subprocess.Popen(
            [updater_path, application_path, update_path, str(os.getpid())],
            close_fds=True,
        )
        message_queue.put(("app_update_started", None))
    except Exception as error:
        if update_path and os.path.exists(update_path):
            os.remove(update_path)
        if updater_update_path and os.path.exists(updater_update_path):
            os.remove(updater_update_path)
        message_queue.put(("app_update_error", str(error)))
