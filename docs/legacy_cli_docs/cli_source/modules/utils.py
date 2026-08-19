import re
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """
    Removes characters that Windows doesn't allow in filenames.
    """
    return re.sub(r'[<>:"/\\|?*]', "", name).strip()


def seconds_to_timestamp(seconds: int) -> str:
    """
    Converts seconds to HH:MM:SS.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02}:{minutes:02}:{secs:02}"


def timestamp_to_seconds(timestamp: str) -> int:
    """
    Converts HH:MM:SS into seconds.
    """
    h, m, s = map(int, timestamp.split(":"))
    return h * 3600 + m * 60 + s


def save_text(path: Path, text: str):
    """
    Saves text to a UTF-8 file.
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def load_text(path: Path) -> str:
    """
    Loads UTF-8 text.
    """
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """CLI yes/no prompt. Blank input falls back to `default`."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    answer = input(prompt + suffix).strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def ask_choice(prompt: str, options: list, default_index: int = 0) -> str:
    """
    Prints a numbered list of options and returns the chosen string.
    Blank input picks default_index.
    """
    print(prompt)
    for i, opt in enumerate(options, start=1):
        marker = " (default)" if (i - 1) == default_index else ""
        print(f"  {i}. {opt}{marker}")

    raw = input("> ").strip()
    if not raw:
        return options[default_index]

    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        pass

    print("Didn't recognize that choice, using default.")
    return options[default_index]


def _open_native_file_browser() -> str:
    """
    Opens the OS's normal file-picker window (the same one every app
    uses) and returns the chosen path, or "" if cancelled. Ships with
    standard Python on Windows and Mac -- no extra install needed.
    Sidesteps drag-and-drop entirely, which depends on the terminal app
    actually being focused at the right moment and doesn't work the
    same way in every terminal.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print("A file-browser window isn't available in this Python install -- type the path instead.")
        return ""

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)  # bring the dialog to the front
        path = filedialog.askopenfilename(title="Select a video or audio file")
        root.destroy()
        return path
    except tk.TclError:
        print("Couldn't open a file-browser window on this system -- type the path instead.")
        return ""


def prompt_file_path(message: str) -> str:
    """
    Shared "give me a file" prompt used anywhere the toolkit needs a
    local file: offers a native Browse window as an alternative to
    typing or drag-and-dropping a path, since drag-and-drop only works
    if the terminal window happens to be focused at the exact right
    moment -- easy to fumble, especially on Windows.

    Returns the cleaned path string (quotes stripped), or "" if the
    user cancels/enters nothing.
    """
    choice = ask_choice(
        f"\n{message}",
        ["Type or drag-and-drop the path here", "Open a file browser window instead"],
    )

    if choice.startswith("Open a file browser"):
        path = _open_native_file_browser()
        if not path:
            print("No file selected.")
        return path

    raw = input("Path: ").strip()
    return raw.strip('"\'')