import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

MAX_WORKERS = 8

def log(msg):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)
    root.update_idletasks()

def select_modlist():
    path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
    if path:
        modlist_path_var.set(path)

def select_output_folder():
    path = filedialog.askdirectory()
    if path:
        output_dir_var.set(path)

def start_download():
    modlist_path = Path(modlist_path_var.get())
    output_dir = Path(output_dir_var.get())
    output_dir.mkdir(exist_ok=True)

    with open(modlist_path, "r") as f:
        mods = json.load(f)

    progress_bar["maximum"] = len(mods)
    progress_bar["value"] = 0

    def download_mod(mod):
        project_id = mod["url"].split("/")[-1]
        version_str = mod["version"]

        try:
            versions = requests.get(
                f"https://api.modrinth.com/v2/project/{project_id}/version"
            ).json()

            candidates = [
                version_str,
                version_str + "+fabric",
                version_str + "-fabric",
            ]

            version_data = next(
                (
                    v for v in versions
                    if v["version_number"] in candidates
                    or v["version_number"].endswith(version_str)
                    or v["version_number"].endswith(version_str + "+fabric")
                    or v["version_number"].endswith(version_str + "-fabric")
                ),
                None
            )

            if not version_data:
                return f"❌ {mod['name']}: version {version_str} NOT FOUND"

            file_info = version_data["files"][0]
            for f in version_data["files"]:
                if "fabric" in f["filename"].lower():
                    file_info = f
                    break

            download_url = file_info["url"]
            filename = file_info["filename"]
            file_path = output_dir / filename

            if file_path.exists():
                return f"✅ {filename} already exists"

            data = requests.get(download_url).content
            with open(file_path, "wb") as f:
                f.write(data)

            return f"⬇️  Downloaded {filename}"

        except Exception as e:
            return f"⚠️ Error downloading {mod['name']}: {e}"

    def run_parallel():
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(download_mod, mod) for mod in mods]
            for future in as_completed(futures):
                msg = future.result()
                log(msg)
                progress_bar["value"] += 1

    run_parallel()
    log("✅ All done!")

# *********** Gui stuff ****************
root = tk.Tk()
root.title("Modrinth Mod Downloader")

modlist_path_var = tk.StringVar()
output_dir_var = tk.StringVar(value="mods")

ttk.Label(root, text="Modlist File:").grid(row=0, column=0, sticky="w")
ttk.Entry(root, textvariable=modlist_path_var, width=50).grid(row=0, column=1)
ttk.Button(root, text="Browse", command=select_modlist).grid(row=0, column=2)

ttk.Label(root, text="Output Folder:").grid(row=1, column=0, sticky="w")
ttk.Entry(root, textvariable=output_dir_var, width=50).grid(row=1, column=1)
ttk.Button(root, text="Browse", command=select_output_folder).grid(row=1, column=2)

ttk.Button(root, text="Start Download", command=start_download).grid(row=2, column=1, pady=10)

progress_bar = ttk.Progressbar(root, length=400)
progress_bar.grid(row=3, column=0, columnspan=3, pady=5)

log_box = scrolledtext.ScrolledText(root, width=60, height=15)
log_box.grid(row=4, column=0, columnspan=3, pady=5)

root.mainloop()
