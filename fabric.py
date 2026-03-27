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
# Kopiowanie plików, nadpisywanie obecnych
                for item in os.listdir(extracted_root):
                    # Pomijaj folder "mods", aby nie usunąć zainstalowanych modyfikacji
                    if item.lower() == "mods":
                        continue
                        
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
    console.print("[bold bright_yellow]--- PyCMD Reseting ---[/bold bright_yellow]\n")
    
    with console.status("Sprawdzanie aktualizacji...", spinner="dots"):
        remote_v = get_remote_version()

    console.print(f"Wersja do której zostanie zresetowane PyCMD: [cyan]{remote_v}[/cyan]\n")
    
    if remote_v == "0.0.0":
        console.print("[red]Nie udało się pobrać informacji o nowej wersji.[/red]")
        input("\nNaciśnij Enter, aby wyjść...")
        return
#ff0000
    if remote_v:
        console.print(f"[bold #e33325]UWAGA! Stracisz wszystkie dane PyCMD. [/bold #FF8C00]")
        choice = console.input("Czy chcesz zresetartować PyCMD teraz? ([#00FF00]T[/#00FF00]/[#FF0000]N[/#FF0000]): ").strip().lower()
        
        if choice in ['t', 'y', 'tak', 'yes']:
            success = download_and_update()
            if success:
                console.print("\n[bold green]✅ Resetowanie zakończone pomyślnie![/bold green]")
                console.print("[yellow]Uruchom ponownie PyCMD, aby zastosować zmiany.[/yellow]")
            else:
                console.print("\n[bold red]❌ Resetowanie nie powiodło się.[/bold red]")
        else:
            console.print("Anulowano resetowanie.")
    else:
        console.print("[green]Posiadasz najnowszą wersję PyCMD.[/green]")
        
    input("\nNaciśnij Enter, aby wyjść...")

if __name__ == "__main__":
    main()