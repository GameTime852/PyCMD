import os
import sys
import time
import shutil
import urllib.request
import urllib.error
import zipfile
import tempfile
from pathlib import Path

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Brak modułu 'rich'. Zainstaluj go komendą: pip install rich")
    sys.exit(1)

console = Console()

# --- KONFIGURACJA GITHUBA ---
# Zmień te dane, jeśli nazwa Twojego repozytorium lub brancha jest inna
GITHUB_USER = "gametime852"
GITHUB_REPO = "pycmd"
BRANCH = "main"

CONFIG_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/config.txt"
ZIP_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/refs/heads/{BRANCH}.zip"

def get_local_version() -> str:
    """Odczytuje lokalną wersję z pliku config.txt."""
    config_path = Path('config.txt')
    if not config_path.exists():
        return "0.0.0"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("version ="):
                    return line.split('=')[1].strip()
    except Exception as e:
        console.print(f"[red]Błąd podczas czytania lokalnego config.txt: {e}[/red]")
    return "0.0.0"

def get_remote_version() -> str:
    """Pobiera najnowszą wersję z serwera GitHub."""
    try:
        req = urllib.request.Request(CONFIG_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            for line in content.splitlines():
                if line.startswith("version ="):
                    return line.split('=')[1].strip()
    except urllib.error.URLError as e:
        console.print(f"[red]Brak połączenia z internetem lub repozytorium: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Nieoczekiwany błąd: {e}[/red]")
    
    return "0.0.0"

def parse_version(v_str: str) -> tuple:
    """Konwertuje ciąg znaków wersji (np. 1.1.1) na tuple do porównania."""
    try:
        return tuple(map(int, v_str.split('.')))
    except ValueError:
        return (0, 0, 0)

def download_and_update():
    """Pobiera i instaluje aktualizację."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        
        # Krok 1: Pobieranie ZIP
        task1 = progress.add_task("[cyan]Pobieranie plików z GitHub...", total=None)
        try:
            req = urllib.request.Request(ZIP_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                zip_data = response.read()
            progress.update(task1, completed=True)
        except Exception as e:
            console.print(f"[red]Błąd podczas pobierania aktualizacji: {e}[/red]")
            return False

        # Krok 2: Wypakowanie i kopiowanie
        task2 = progress.add_task("[yellow]Instalowanie aktualizacji...", total=None)
        try:
            # Użycie folderu tymczasowego
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "update.zip")
                
                # Zapisz pobrany ZIP
                with open(zip_path, 'wb') as f:
                    f.write(zip_data)
                
                # Rozpakuj ZIP
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Struktura ZIP z GitHuba zwykle posiada główny folder np. pycmd-main
                extracted_root = os.path.join(temp_dir, f"{GITHUB_REPO}-{BRANCH}")
                if not os.path.exists(extracted_root):
                    # Zabezpieczenie, jeśli nazwa folderu wewnątrz ZIP jest inna
                    extracted_root = os.path.join(temp_dir, os.listdir(temp_dir)[0])
                
                # Kopiowanie plików, nadpisywanie obecnych
                for item in os.listdir(extracted_root):
                    source = os.path.join(extracted_root, item)
                    destination = os.path.join(os.getcwd(), item)
                    
                    if os.path.isdir(source):
                        shutil.copytree(source, destination, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source, destination)
            
            progress.update(task2, completed=True)
            return True
            
        except Exception as e:
            console.print(f"[bold red]Krytyczny błąd podczas instalacji plików: {e}[/bold red]")
            return False

def main():
    console.clear()
    console.print("[bold bright_yellow]--- PyCMD Updater ---[/bold bright_yellow]\n")
    
    with console.status("Sprawdzanie aktualizacji...", spinner="dots"):
        local_v = get_local_version()
        remote_v = get_remote_version()
    
    console.print(f"Obecna wersja: [cyan]{local_v}[/cyan]")
    console.print(f"Najnowsza stabilna dostępna wersja: [cyan]{remote_v}[/cyan]\n")
    
    if remote_v == "0.0.0":
        console.print("[red]Nie udało się pobrać informacji o nowej wersji.[/red]")
        input("\nNaciśnij Enter, aby wyjść...")
        return

    if parse_version(remote_v) > parse_version(local_v):
        console.print("[bold green]Dostępna jest nowa aktualizacja![/bold green]")
        choice = console.input("Czy chcesz pobrać i zainstalować aktualizację teraz? (T/N): ").strip().lower()
        
        if choice in ['t', 'y', 'tak', 'yes']:
            success = download_and_update()
            if success:
                console.print("\n[bold green]✅ Aktualizacja zakończona pomyślnie![/bold green]")
                console.print("[yellow]Uruchom ponownie PyCMD, aby zastosować zmiany.[/yellow]")
            else:
                console.print("\n[bold red]❌ Aktualizacja nie powiodła się.[/bold red]")
        else:
            console.print("Anulowano aktualizację.")
    else:
        console.print("[green]Posiadasz najnowszą wersję PyCMD.[/green]")
        
    input("\nNaciśnij Enter, aby wyjść...")

if __name__ == "__main__":
    main()