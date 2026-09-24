import os
import subprocess
import sys
from pathlib import Path


def open_path(path):
    path = str(Path(path).resolve())
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])
