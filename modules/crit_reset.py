from rich.console import Console
import time

def main():

    console = Console()

    #dots (standardowe kropki) ✅
    # 'spinner' to nazwa animacji. "dots" to klasyczne kropki kręcące się w kółko.
    with console.status("Uruchamiam ponownie po krytycznym błędzie...",spinner="dots", spinner_style="#00FFEA"):
        # Tutaj umieść swój kod, który zajmuje czas
        time.sleep(2)
