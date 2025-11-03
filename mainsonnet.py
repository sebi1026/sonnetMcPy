import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
from tkinter import filedialog
import threading

MAX_WORKERS = 8

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class sonnetApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("sonnetMcPy")
        self.geometry("700x500")
        self.iconbitmap(False, "images/sonnetlogo.ico")

        self.modlist_path = ctk.StringVar()
        self.output_dir = ctk.StringVar(value="mods")

        # UI Layout
        ctk.CTkLabel(self, text="Modlist File:").pack(anchor="w", padx=10, pady=(10, 0))
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=10)
        ctk.CTkEntry(file_frame, textvariable=self.modlist_path).pack(side="left", fill="x", expand=True, padx=5, pady=5)
        ctk.CTkButton(file_frame, text="Browse", command=self.select_modlist).pack(side="right", padx=5)

        ctk.CTkLabel(self, text="Output Folder:").pack(anchor="w", padx=10, pady=(10, 0))
        folder_frame = ctk.CTkFrame(self)
        folder_frame.pack(fill="x", padx=10)
        ctk.CTkEntry(folder_frame, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=5, pady=5)
        ctk.CTkButton(folder_frame, text="Browse", command=self.select_output_folder).pack(side="right", padx=5)

        self.start_button = ctk.CTkButton(self, text="Start Download", command=self.start_download_thread)
        self.start_button.pack(pady=10)

        # Progress Bars
        self.overall_progress = ctk.CTkProgressBar(self)
        self.overall_progress.pack(fill="x", padx=10, pady=(5, 0))
        self.overall_progress.set(0)

        self.current_progress = ctk.CTkProgressBar(self)
        self.current_progress.pack(fill="x", padx=10, pady=(5, 10))
        self.current_progress.set(0)

        # Log Output
        self.log_box = ctk.CTkTextbox(self, height=250)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.update_idletasks()

    def select_modlist(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if path:
            self.modlist_path.set(path)

    def select_output_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def start_download_thread(self):
        threading.Thread(target=self.start_download, daemon=True).start()

    def download_file(self, url, path):
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_length = int(r.headers.get("content-length", 1))
            downloaded = 0

            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    self.current_progress.set(downloaded / total_length)

    def start_download(self):
        modlist = Path(self.modlist_path.get())
        output_dir = Path(self.output_dir.get())
        output_dir.mkdir(exist_ok=True)

        mods = json.load(open(modlist, "r"))
        total_mods = len(mods)
        self.overall_progress.set(0)

        def process_mod(mod):
            project_id = mod["url"].split("/")[-1]
            version_str = mod["version"]

            versions = requests.get(f"https://api.modrinth.com/v2/project/{project_id}/version").json()

            candidates = [
                version_str,
                version_str + "+fabric",
                version_str + "-fabric",
            ]

            version_data = next(
                (
                    v for v in versions
                    if any(
                        c in v["version_number"] or v["version_number"].endswith(c)
                        for c in candidates
                    )
                ),
                None
            )

            if not version_data:
                return f"❌ {mod['name']}: version not found"

            file = version_data["files"][0]
            for f in version_data["files"]:
                if "fabric" in f["filename"].lower():
                    file = f
                    break

            url = file["url"]
            filename = file["filename"]
            filepath = output_dir / filename

            if filepath.exists():
                return f"✅ {filename} exists, skipped"

            self.current_progress.set(0)
            self.download_file(url, filepath)
            return f"⬇️ Downloaded {filename}"

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for i, result in enumerate(executor.map(process_mod, mods), start=1):
                self.log(result)
                self.overall_progress.set(i / total_mods)

        self.log("✅ Complete!")


if __name__ == "__main__":
    app = sonnetApp()
    app.mainloop()
