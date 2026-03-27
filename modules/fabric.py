from rich.console import Console
import time
import os

def main():

    console = Console()

    #dots (standardowe kropki) ✅
    # 'spinner' to nazwa animacji. "dots" to klasyczne kropki kręcące się w kółko.
    with console.status("Restartowanie PyCMD...",spinner="dots", spinner_style="white"):
        # Tutaj umieść swój kod, który zajmuje czas
        time.sleep(2)

        os.system("cd ..")
        os.system("python fabric.py")
