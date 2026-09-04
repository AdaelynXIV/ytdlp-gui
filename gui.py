import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from packaging.version import parse as parse_version

from config import (
    ACCENT,
    BG,
    CONSOLE_BG,
    ERROR,
    FG,
    FORMAT_OPTIONS,
    INFO,
    MUTED,
    PANEL,
    OUTPUT_DIR,
    WARNING,
    WINDOW_SIZE,
    WINDOW_TITLE,
)
from services import (
    check_app_update,
    check_ffmpeg_versions,
    check_versions,
    download_app_update,
    run_download,
    run_update,
)


class YtdlpApp:
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.message_queue = queue.Queue()
        self.pending_app_update_url = None
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self._build_styles()
        self._build_widgets()
        self._start_background_tasks()

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Bold.TLabel", background=BG, foreground=FG, font=("Segoe UI", 10, "bold"))
        style.configure(
            "TCombobox",
            fieldbackground=PANEL,
            background=PANEL,
            foreground=FG,
            relief="flat",
            borderwidth=0,
            padding=6,
            arrowcolor=FG,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", PANEL)],
            foreground=[("readonly", FG)],
            selectbackground=[("readonly", ACCENT)],
            selectforeground=[("readonly", "#111111")],
        )
        style.configure("TProgressbar", background=ACCENT, throughcolor=PANEL)
        style.configure("TButton", background=PANEL, foreground=FG, font=("Segoe UI", 10), padding=6)
        style.map("TButton", background=[("active", "#3a3d4d")])
        self.root.configure(bg=BG)

    def _build_widgets(self):
        self.version_label = ttk.Label(self.root, text="yt-dlp: checking...", foreground=MUTED)
        self.version_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.ffmpeg_version_label = ttk.Label(
            self.root, text="FFmpeg: checking...", foreground=MUTED
        )
        self.ffmpeg_version_label.pack(anchor="w", padx=20, pady=(0, 5))

        ttk.Label(self.root, text="URL", style="Bold.TLabel").pack(anchor="w", padx=20, pady=(15, 0))
        self.url_entry = tk.Entry(self.root, font=("Segoe UI", 11), bg=PANEL, fg=FG, insertbackground=FG, relief="flat")
        self.url_entry.pack(fill="x", padx=20, pady=(4, 10))

        ttk.Label(self.root, text="Format", style="Bold.TLabel").pack(anchor="w", padx=20)
        self.format_var = tk.StringVar(value="Best Quality (video + audio)")
        self.format_menu = ttk.Combobox(
            self.root,
            textvariable=self.format_var,
            values=list(FORMAT_OPTIONS.keys()),
            state="readonly",
        )
        self.format_menu.pack(fill="x", padx=20, pady=(4, 10))
        popdown = self.format_menu.tk.call("ttk::combobox::PopdownWindow", str(self.format_menu))
        self.format_menu.tk.call(
            f"{popdown}.f.l",
            "configure",
            "-background", PANEL,
            "-foreground", FG,
            "-selectbackground", ACCENT,
            "-selectforeground", "#111111",
        )

        ttk.Label(self.root, text="Output Directory", style="Bold.TLabel").pack(anchor="w", padx=20)
        folder_frame = ttk.Frame(self.root)
        folder_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.folder_label = ttk.Label(folder_frame, text=self.output_dir, anchor="w")
        self.folder_label.pack(side="left", fill="x", expand=True)
        tk.Button(folder_frame, text="Browse", command=self.browse_folder, relief="flat").pack(side="right")

        self.progress = ttk.Progressbar(self.root, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=20, pady=(0, 5))
        self.status_label = ttk.Label(self.root, text="Idle", anchor="w", style="Bold.TLabel")
        self.status_label.pack(fill="x", padx=20)

        self.console = scrolledtext.ScrolledText(
            self.root,
            height=12,
            bg=CONSOLE_BG,
            fg=FG,
            font=("Consolas", 9),
            relief="flat",
            borderwidth=0,
        )
        self.console.configure(state="disabled")
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=20, pady=(5, 0))
        ttk.Label(toolbar, text="Console", style="Bold.TLabel").pack(side="left")
        self.clear_console_button = tk.Button(
            toolbar,
            text="Clear Console",
            command=self.clear_console,
            bg=PANEL,
            fg=FG,
            font=("Segoe UI", 9),
            relief="flat",
            padx=8,
            pady=3,
            state="disabled",
        )
        self.clear_console_button.pack(side="right")
        self.console.pack(fill="both", padx=20, pady=(3, 15), expand=True)
        self.console.tag_config("warning", foreground=WARNING)
        self.console.tag_config("error", foreground=ERROR)
        self.console.tag_config("info", foreground=INFO)
        self.console.tag_config("bold", foreground=FG, font=("Consolas", 9, "bold"))

        self.download_button = tk.Button(
            self.root,
            text="Download",
            command=self.start_download,
            bg=ACCENT,
            fg="#111111",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=10,
            pady=6,
        )
        self.download_button.pack(pady=(0, 10))
        self.update_button = tk.Button(
            self.root,
            text="Update yt-dlp / ffmpeg",
            command=self.start_update,
            bg="#555555",
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
        )
        self.update_button.pack(pady=(0, 10))
        self.app_update_button = tk.Button(
            self.root,
            text="Check for App Updates",
            command=self.start_app_update,
            bg="#555555",
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
        )
        self.app_update_button.pack(pady=(0, 10))

    def _start_background_tasks(self):
        threading.Thread(
            target=check_versions, args=(self.message_queue,), daemon=True
        ).start()
        threading.Thread(
            target=check_ffmpeg_versions, args=(self.message_queue,), daemon=True
        ).start()
        self.root.after(100, self.poll_queue)

    def browse_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.output_dir)
        if chosen:
            self.output_dir = chosen
            self.folder_label.config(text=self.output_dir)

    def clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")
        self.clear_console_button.config(state="disabled")

    def log(self, text, level="normal"):
        self.console.configure(state="normal")
        self.console.insert("end", text + "\n", level)
        self.console.see("end")
        self.console.configure(state="disabled")
        self.clear_console_button.config(state="normal")

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log("Please enter a URL first.")
            return
        self.download_button.config(state="disabled")
        self.progress["value"] = 0
        self.status_label.config(text="Starting download...")
        self.log(f"\n--- Download Started: {url} ---", "bold")
        threading.Thread(
            target=run_download,
            args=(url, self.format_var.get(), self.output_dir, self.message_queue),
            daemon=True,
        ).start()

    def start_update(self):
        self.update_button.config(state="disabled")
        threading.Thread(
            target=run_update, args=(self.message_queue,), daemon=True
        ).start()

    def start_app_update(self):
        self.app_update_button.config(state="disabled")
        threading.Thread(
            target=check_app_update, args=(self.message_queue,), daemon=True
        ).start()

    def offer_app_update(self, version, download_url, updater_download_url):
        self.pending_app_update_url = download_url
        install = messagebox.askyesno(
            "Update available",
            f"Version {version} is available. Download and install it now?",
        )
        if install:
            threading.Thread(
                target=download_app_update,
                args=(download_url, updater_download_url, self.message_queue),
                daemon=True,
            ).start()
        else:
            self.app_update_button.config(state="normal")

    def poll_queue(self):
        try:
            while True:
                kind, *data = self.message_queue.get_nowait()
                if kind == "log":
                    self.log(*data)
                elif kind == "progress":
                    percent, text = data
                    self.progress["value"] = percent
                    self.status_label.config(text=text)
                elif kind == "done":
                    self.download_button.config(state="normal")
                    if data[0] == 0:
                        self.status_label.config(text="Done")
                        self.log("--- Finished Successfully ---", "bold")
                    else:
                        self.status_label.config(text="Failed")
                elif kind == "update_done":
                    self.update_button.config(state="normal")
                elif kind == "version":
                    self.update_version_label(*data)
                elif kind == "ffmpeg_version":
                    self.update_ffmpeg_version_label(*data)
                elif kind == "ffmpeg_version_error":
                    self.ffmpeg_version_label.config(
                        text="FFmpeg: version check failed", foreground=WARNING
                    )
                    self.log(f"FFmpeg version check failed: {data[0]}", "warning")
                elif kind == "app_update_current":
                    self.log(f"Application is up to date (v{data[0]}).", "info")
                    self.app_update_button.config(state="normal")
                elif kind == "app_update_available":
                    self.offer_app_update(*data)
                elif kind == "app_update_started":
                    self.log("Installing update and restarting...", "info")
                    self.root.destroy()
                elif kind == "app_update_error":
                    self.log(f"Application update failed: {data[0]}", "error")
                    self.app_update_button.config(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def update_version_label(self, installed, latest):
        if latest is None:
            self.version_label.config(text=f"yt-dlp: v{installed} (couldn't check for updates)")
        elif parse_version(installed) >= parse_version(latest):
            self.version_label.config(text=f"yt-dlp: v{installed} (up-to-date)")
        else:
            self.version_label.config(
                text=f"yt-dlp: v{installed} -> v{latest} available",
                foreground=WARNING,
            )

    def update_ffmpeg_version_label(self, binary_version, installed, latest):
        if latest is None:
            self.ffmpeg_version_label.config(
                text=f"FFmpeg: {binary_version} (imageio-ffmpeg {installed}; couldn't check for updates)"
            )
        elif parse_version(installed) >= parse_version(latest):
            self.ffmpeg_version_label.config(
                text=f"FFmpeg: {binary_version} (imageio-ffmpeg {installed}; up-to-date)"
            )
        else:
            self.ffmpeg_version_label.config(
                text=f"FFmpeg: {binary_version} (imageio-ffmpeg {installed} -> {latest} available)",
                foreground=WARNING,
            )

    def run(self):
        self.root.mainloop()
