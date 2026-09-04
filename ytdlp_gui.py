from dependencies import ensure_dependencies

ensure_dependencies()

from gui import YtdlpApp


if __name__ == "__main__":
    YtdlpApp().run()
