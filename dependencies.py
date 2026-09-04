import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version

from config import IS_FROZEN


def ensure_package(pip_name, import_name=None, minimum_version=None):
    import_name = import_name or pip_name
    try:
        __import__(import_name)
        if minimum_version:
            from packaging.version import parse

            if parse(version(pip_name)) < parse(minimum_version):
                raise ImportError
    except (ImportError, PackageNotFoundError):
        print(f"Installing {pip_name}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", pip_name]
        )


def ensure_dependencies():
    if IS_FROZEN:
        return

    ensure_package("packaging")
    ensure_package("yt-dlp", "yt_dlp")
    ensure_package("curl-cffi", "curl_cffi", minimum_version="0.10.0")
    ensure_package("imageio-ffmpeg", "imageio_ffmpeg")
    ensure_package("requests")
