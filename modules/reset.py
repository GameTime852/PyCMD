from rich.console import Console
import time

def main():

    console = Console()

    #dots (standardowe kropki) ✅
    # 'spinner' to nazwa animacji. "dots" to klasyczne kropki kręcące się w kółko.
    with console.status("Uruchamiam ponownie...",spinner="dots", spinner_style="white"):
        # Tutaj umieść swój kod, który zajmuje czas
        time.sleep(2)
