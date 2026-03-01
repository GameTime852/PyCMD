import os
import json
import urllib.request
import urllib.parse
import urllib.error
import zipfile
import tempfile
import shutil
import sys

try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Brak modułu 'rich'. Zainstaluj go komendą: pip install rich")
    sys.exit(1)

console = Console()

# Określanie ścieżek niezależnie od miejsca uruchomienia
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Zakładamy, że to folder modules/
ROOT_DIR = os.path.dirname(SCRIPT_DIR)                  # Główny folder PyCMD
MODS_DIR = os.path.join(ROOT_DIR, "mods")               # Docelowy folder na mody

def search_github_for_mods(query: str) -> list:
    """Przeszukuje GitHub API w poszukiwaniu modów do PyCMD."""
    # Dodajemy słowo 'pycmd', aby upewnić się, że szukamy modów do Twojego programu
    # Można też szukać po tagach, np. 'topic:pycmd-mod'
    search_query = urllib.parse.quote(f"{query} pycmd")
    url = f"https://api.github.com/search/repositories?q={search_query}&sort=stars&order=desc&per_page=10"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'PyCMD-ModManager/1.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('items', [])
    except urllib.error.HTTPError as e:
        if e.code == 403:
            console.print("[red]Przekroczono limit zapytań do API GitHuba. Spróbuj ponownie za chwilę.[/red]")
        else:
            console.print(f"[red]Błąd serwera: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Błąd podczas wyszukiwania: {e}[/red]")
    
    return []

def display_mods(mods: list):
    """Wyświetla znalezione mody w formie czytelnej tabeli."""
    table = Table(title="Znalezione Modyfikacje na GitHubie")
    
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Nazwa / Repozytorium", style="magenta")
    table.add_column("Opis", style="white")
    table.add_column("Gwiazdki ⭐", justify="right", style="yellow")

    for idx, mod in enumerate(mods):
        # Skracanie opisu, jeśli jest za długi
        desc = mod.get('description') or "Brak opisu"
        if len(desc) > 60:
            desc = desc[:57] + "..."
            
        table.add_row(
            str(idx + 1),
            f"{mod['owner']['login']}/[bold]{mod['name']}[/bold]",
            desc,
            str(mod['stargazers_count'])
        )
        
    console.print(table)

def download_and_install_mod(mod_data: dict):
    """Pobiera i instaluje wybranego moda."""
    repo_full_name = mod_data['full_name']
    default_branch = mod_data.get('default_branch', 'main')
    zip_url = f"https://github.com/{repo_full_name}/archive/refs/heads/{default_branch}.zip"
    
    if not os.path.exists(MODS_DIR):
        os.makedirs(MODS_DIR)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        
        # Pobieranie
        task1 = progress.add_task(f"[cyan]Pobieranie {repo_full_name}...", total=None)
        try:
            req = urllib.request.Request(zip_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                zip_data = response.read()
            progress.update(task1, completed=True)
        except Exception as e:
            console.print(f"[red]Błąd pobierania moda: {e}[/red]")
            return

        # Instalacja
        task2 = progress.add_task("[yellow]Instalowanie moda...", total=None)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "mod.zip")
                with open(zip_path, 'wb') as f:
                    f.write(zip_data)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Odnajdywanie wypakowanego folderu głównego (np. nazwa_repo-main)
                extracted_folders = [f for f in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, f))]
                if not extracted_folders:
                    raise Exception("Archiwum ZIP jest puste.")
                
                mod_root = os.path.join(temp_dir, extracted_folders[0])
                
                installed_files = 0
                
                # Sposób 1: Mod posiada własny folder 'mods' lub 'modules'
                mod_specific_dir = None
                if os.path.exists(os.path.join(mod_root, "mods")):
                    mod_specific_dir = os.path.join(mod_root, "mods")
                elif os.path.exists(os.path.join(mod_root, "modules")):
                    mod_specific_dir = os.path.join(mod_root, "modules")
                
                if mod_specific_dir and os.path.isdir(mod_specific_dir):
                    for item in os.listdir(mod_specific_dir):
                        if item.endswith(".py"):
                            shutil.copy2(os.path.join(mod_specific_dir, item), os.path.join(MODS_DIR, item))
                            installed_files += 1
                else:
                    # Sposób 2: Kopiujemy wszystkie pliki .py z głównego folderu repozytorium
                    for item in os.listdir(mod_root):
                        if item.endswith(".py") and item.lower() != "setup.py":
                            shutil.copy2(os.path.join(mod_root, item), os.path.join(MODS_DIR, item))
                            installed_files += 1
                
                progress.update(task2, completed=True)
                
                if installed_files > 0:
                    console.print(f"[bold green]✅ Pomyślnie zainstalowano {installed_files} plików z {repo_full_name} do folderu 'mods'![/bold green]")
                else:
                    console.print(f"[bold yellow]⚠️ Pobrane repozytorium {repo_full_name} nie zawierało żadnych plików .py w głównym folderze ani w folderach 'mods'/'modules'.[/bold yellow]")

        except Exception as e:
            console.print(f"[bold red]Błąd podczas instalacji moda: {e}[/bold red]")

def main():
    console.clear()
    console.print("[bold bright_green]--- PyCMD Mod Manager ---[/bold bright_green]")
    console.print("Tutaj możesz wyszukiwać i instalować modyfikacje stworzone przez społeczność.\n")
    
    while True:
        query = console.input("[cyan]Wpisz czego szukasz (lub 'q' aby wyjść): [/cyan]").strip()
        
        if query.lower() in ['q', 'quit', 'wyjdz', 'exit']:
            break
        if not query:
            continue
            
        with console.status("Przeszukiwanie GitHuba...", spinner="dots"):
            mods = search_github_for_mods(query)
            
        if not mods:
            console.print("[yellow]Nie znaleziono żadnych modów spełniających Twoje kryteria. Spróbuj innych słów.[/yellow]\n")
            continue
            
        display_mods(mods)
        
        choice = console.input("\n[magenta]Wpisz ID moda, aby go zainstalować (lub '0' aby wrócić do wyszukiwania): [/magenta]").strip()
        
        if choice.isdigit():
            choice_idx = int(choice)
            if choice_idx == 0:
                continue
            elif 1 <= choice_idx <= len(mods):
                selected_mod = mods[choice_idx - 1]
                confirm = console.input(f"Czy na pewno chcesz zainstalować [bold]{selected_mod['name']}[/bold]? (t/n): ").strip().lower()
                if confirm in ['t', 'tak', 'y', 'yes']:
                    download_and_install_mod(selected_mod)
                else:
                    console.print("Anulowano instalację.")
            else:
                console.print("[red]Nieprawidłowe ID.[/red]")
        else:
            console.print("[red]Proszę wpisać cyfrę.[/red]")
            
        print("\n" + "-"*40 + "\n")

if __name__ == "__main__":
    main()