import os
import time
import importlib.util
import sys
import logging
import json  # <--- Konieczne do zapisu configu modów
import atexit
from pathlib import Path
import shutil
import rich.console as console
from rich.prompt import Prompt
from rich.text import Text
import stdiomask
import traceback
import hashlib
import requests


console = console.Console()


import updater
from modules import getmods, help, info, Start, load_exit2, reset, first, crit_repair, crit_reset

admin = False
root = False

def stop():
    logging.info("Zamykanie...")
    clear()
    load_exit2.load_exit()
    try:
        with open('config.txt', 'w', encoding='utf-8') as f:
            f.writelines(["started = false\n"] + lines[1:])
    except: pass
    exit()
first_file = Path("first")
if first_file.exists() and first_file.is_file():
    first.main()
    logging.info("First Start!")
    first_file.unlink(missing_ok=True)

class TestCrash(Exception):
    def __init__(self, message="To jest testowy błąd krytyczny!"):
        self.message = message
        super().__init__(message)
        


# --- KONFIGURACJA LOGÓW ---
logging.basicConfig(
    filename='logs.txt',
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(module)s:%(funcName)s] %(message)s',
    datefmt='%H:%M:%S',
    filemode='a', # Zmiana z 'w' na 'a' (append), aby restart (Safe Critical) nie czyścił od razu logu błędu!
    encoding='utf-8'
)

# --- CZYSZCZENIE LOGÓW PO ZAMKNIĘCIU ---
def clean_logs_on_exit():
    """Funkcja uruchamiana automatycznie przy zamykaniu programu."""
    logging.shutdown()
    try:
        with open('logs.txt', 'w', encoding='utf-8') as f:
            pass 
    except Exception:
        pass

atexit.register(clean_logs_on_exit)

# --- SYSTEM SAFE CRITICAL (GLOBAL EXCEPTION HANDLER) ---

def safe_critical_handler(exc_type, exc_value, exc_tb):
    """Przechwytuje krytyczne błędy, chroni przed crashami i restartuje system."""
    
    # 1. Dokładny zapis błędu do ukrytych logów
    logging.critical("--- WYSTĄPIŁ BŁĄD KRYTYCZNY SYSTEMU (SAFE CRITICAL) ---")
    error_details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical(f"\n{error_details}")
    logging.critical("Wymuszanie trybu Safe Critical i restartu.")

    # 2. Ładny komunikat "Blue Screen" dla użytkownika
    from rich.panel import Panel
    error_msg = (
        "[bold red]System napotkał krytyczny błąd, którego nie mógł zignorować.[/bold red]\n\n"
        f"[yellow]Typ błędu:[/] {exc_type.__name__}\n"
        f"[yellow]Opis błędu:[/] {exc_value}\n\n"
        "[cyan]Szczegółowy ślad błędu (Traceback) został bezpiecznie zapisany w logs.txt.[/cyan]\n"
        "[bold white]Trwa zabezpieczanie danych i awaryjne ponowne uruchamianie...[/bold white]"
    )
    
    console.print()
    console.print(Panel(error_msg, title="[blink black on #00FFEA] FATAL ERROR [/blink black on #00FFEA]", border_style="#00FFEA"))

    # 3. Zmiana flagi w config.txt na "critical"
    try:
        with open('config.txt', 'r', encoding='utf-8') as f:
            c_lines = f.readlines()
        
        if c_lines:
            c_lines[0] = "started = critical\n"
            with open('config.txt', 'w', encoding='utf-8') as f:
                f.writelines(c_lines)
    except Exception as e:
        logging.error(f"Nie udało się zmienić statusu na critical: {e}")

    input("\nNaciśnij Enter, aby kontynuować do restartu...")
    # 4. Automatyczny Auto-Reboot po 4 sekundach
    os.system('cls')

    crit_repair.main()
    crit_reset.main()

    try:
        os.system("cd C:\\py")
        os.system("py PyCMD.py")
        exit()
        
    except Exception as e:
        print(f"Błąd podczas resetowania: {e}")

# Rejestracja naszego handlera w rdzeniu Pythona
sys.excepthook = safe_critical_handler

# --- SYSTEM MODÓW I KONFIGURACJA ---

MODS_CONFIG_FILE = 'mods_config.json'
mod_commands = {}

def load_disabled_mods():
    """Wczytuje listę wyłączonych modów z pliku JSON."""
    if not os.path.exists(MODS_CONFIG_FILE):
        return []
    try:
        with open(MODS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_disabled_mods(disabled_list):
    """Zapisuje listę wyłączonych modów."""
    try:
        with open(MODS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(disabled_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Błąd zapisu konfiguracji modów: {e}")

def check_mod_exists(mod_name):
    """Sprawdza, czy mod o danej nazwie istnieje (jako folder lub plik .py)."""
    mods_path = Path('mods')
    # Sprawdź folder
    if (mods_path / mod_name).is_dir() and (mods_path / mod_name / "main.py").exists():
        return True
    # Sprawdź plik .py
    if (mods_path / f"{mod_name}.py").is_file():
        return True
    return False

def load_mods():
    """Ładuje mody w tle, pisząc tylko do logs.txt, pomija wyłączone."""
    mods_path = Path('mods')
    disabled_mods = load_disabled_mods() # Wczytaj wyłączone mody
    
    if not mods_path.exists():
        try:
            mods_path.mkdir()
        except Exception:
            pass 

    logging.info("--- START SYSTEMU ---")
    
    if not any(mods_path.iterdir()):
        logging.info("Brak modów do załadowania.")
        return

    for item in mods_path.iterdir():
        mod_name = item.stem if item.is_file() else item.name
        
        # SPRAWDZANIE CZY MOD JEST WYŁĄCZONY
        if mod_name in disabled_mods:
            logging.info(f"POMINIĘTO (WYŁĄCZONY): {mod_name}")
            continue

        # 1. Foldery
        if item.is_dir():
            main_file = item / "main.py"
            if main_file.exists():
                try:
                    sys.path.append(str(item))
                    spec = importlib.util.spec_from_file_location(item.name, main_file)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    
                    if hasattr(mod, 'register'):
                        mod.register(mod_commands)
                        logging.info(f"ZAŁADOWANO: {item.name}")
                    else:
                        logging.warning(f"ZAŁADOWANO TYLKO STARTUP: {item.name} (brak register)")
                except Exception as e:
                    logging.error(f"BŁĄD KRYTYCZNY w {item.name}: {e}")
                    
        # 2. Pliki .py
        elif item.suffix == ".py" and item.name != "__init__.py":
            try:
                spec = importlib.util.spec_from_file_location(item.stem, item)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                
                if hasattr(mod, 'register'):
                    mod.register(mod_commands)
                    logging.info(f"ZAŁADOWANO: {item.name}")
                else:
                    logging.warning(f"POMINIĘTO: {item.name}")
            except Exception as e:
                logging.error(f"BŁĄD KRYTYCZNY w {item.name}: {e}")

# --- FUNKCJE POMOCNICZE ---

def clear():
    os.system("cls")

# --- INICJALIZACJA ---

file_path = Path('config.txt')
if not file_path.exists():
    file_path.touch()

os.system("cls")
info.info()
print("")
load_mods() 


with open('config.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    if not lines:
        lines = ["started = false\n"]
    started = lines[0]
    ignore = lines[1]
    prefix_line = lines[2]
    prefix = prefix_line.split("prefix = ")[-1].strip()
    admin_login = lines[3].split("admin_login = ")[-1].strip()
    admin_haslo = lines[4].split("admin_haslo = ")[-1].strip()

def zmien_dane():
    global admin_login, admin_haslo, lines, admin
    new_login = input("Ustaw login administratora (Enter dla pozostawienia): ").strip()
    new_password = stdiomask.getpass("Ustaw hasło administratora (Enter dla pozostawienia): ").strip()
    if new_login:
        admin_login = new_login
    if new_password:
        admin_haslo = new_password
    
    new_lines = [started, ignore, f"prefix = {prefix}\n", f"admin_login = {admin_login}\n", f"admin_haslo = {admin_haslo}\n"]
    if len(lines) > 5:
        new_lines.extend(lines[5:])
    
    with open('config.txt', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    lines = new_lines

    clear()
    info.info()
    admin = False

def zmien_prefix():
    global prefix, lines
    new_prefix = input("Ustaw prefix (Enter dla pozostawienia): ").strip()
    if new_prefix:
        prefix = new_prefix
    
    new_lines = [started, ignore, f"prefix = {prefix}\n", f"admin_login = {admin_login}\n", f"admin_haslo = {admin_haslo}\n"]
    if len(lines) > 5:
        new_lines.extend(lines[5:])
        
    with open('config.txt', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    lines = new_lines



if not started == "started = true\n":
    Start.start()
    with open('config.txt', 'w', encoding='utf-8') as f:
        f.writelines(["started = true\n"] + lines[1:])

class adm(Prompt):
    prompt_suffix = Text.from_markup("[bold #ff9221]> [/]")  # Tutaj wpisujesz co chcesz zamiast dwukropka

class root_cmd(Prompt):
    prompt_suffix = Text.from_markup("[bold #00FFEA]> [/]")  # Tutaj wpisujesz co chcesz zamiast dwukropka
# --- PĘTLA GŁÓWNA ---

while True: 
    print("")
    current_directory = os.getcwd()
    try:
        if admin and not root:
            command = adm.ask(f"[bold #ff9221]ADMIN[/bold #ff9221][bold] {prefix} {current_directory}[/bold]")
        elif root:
            command = root_cmd.ask(f"[bold #00FFEA]ROOT[/bold #00FFEA][bold] {prefix} {current_directory}[/bold]")
        else:
            command = input(f"{prefix} {current_directory}> ")
    except EOFError:
        break
        
    command_lower = command.lower()
    
    logging.info(f"CMD: {command}")

    # 1. MODY
    if command_lower in mod_commands:
        try:
            mod_commands[command_lower]()
        except Exception as e:
            print(f"Błąd wykonywania polecenia: {e}")
            logging.error(f"Exception w modzie '{command_lower}': {e}")
        continue

    # 2. ZARZĄDZANIE MODAMI (STYL CD/LS)
    elif command_lower == "mods":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        action = input("Opcja (list/enable/disable/uninstall/install/exit): ").strip().lower()
        disabled_mods = load_disabled_mods()
        
        if action == "list":
            print("\n--- Lista Modów ---")
            mods_path = Path('mods')
            if mods_path.exists():
                found_any = False
                for item in mods_path.iterdir():
                    if (item.is_dir() and (item / "main.py").exists()) or (item.suffix == ".py" and item.name != "__init__.py"):
                        found_any = True
                        name = item.stem if item.is_file() else item.name
                        status = "[WYŁĄCZONY]" if name in disabled_mods else "[AKTYWNY]"
                        print(f" - {name} {status}")
                if not found_any:
                    print("Brak zainstalowanych modów.")
            else:
                print("Folder mods nie istnieje.")
            print("")

        elif action == "disable":
            target_mod = input("Nazwa moda: ").strip()
            if not check_mod_exists(target_mod):
                print(f"Błąd: Mod '{target_mod}' nie istnieje.")
            elif target_mod in disabled_mods:
                print(f"Mod '{target_mod}' jest już wyłączony.")
            else:
                disabled_mods.append(target_mod)
                save_disabled_mods(disabled_mods)
                print(f"Wyłączono moda '{target_mod}'. Zrestartuj PyCMD, aby zastosować zmiany.")

        elif action == "enable":
            target_mod = input("Nazwa moda: ").strip()
            if not check_mod_exists(target_mod):
                print(f"Błąd: Mod '{target_mod}' nie istnieje.")
            elif target_mod not in disabled_mods:
                print(f"Mod '{target_mod}' jest już aktywny.")
            else:
                disabled_mods.remove(target_mod)
                save_disabled_mods(disabled_mods)
                print(f"Włączono moda '{target_mod}'. Zrestartuj PyCMD, aby zastosować zmiany.")
        elif action == "install":
            getmods.main()
        elif action == "uninstall":
            target_mod = input("Nazwa moda do odinstalowania: ").strip()
            mod_path = Path('mods') / target_mod
            
            # --- Funkcja pomocnicza usuwająca problem "WinError 5" ---
            def usun_zablokowane(func, path, exc_info):
                import stat
                try:
                    # Zdejmujemy atrybut 'tylko do odczytu' i próbujemy usunąć ponownie
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    # Jeśli Windows całkowicie blokuje plik (bo np. mod jest załadowany), 
                    # ignorujemy ten konkretny plik, by nie wyrzucić błędu w konsoli
                    pass 

            try:
                if mod_path.is_dir():
                    # Przekazujemy naszą funkcję naprawczą do 'onerror'
                    shutil.rmtree(mod_path, onerror=usun_zablokowane)
                    print(f"Odinstalowano folder moda '{target_mod}'.")
                elif (Path('mods') / f"{target_mod}.py").is_file():
                    print(f"Wybrany mod ({target_mod}) jest plikiem .py. Usuwanie pojedynczego pliku nie jest obsługiwane przez ten system. Usuń ręcznie: {Path('mods') / f'{target_mod}.py'}")
                else:
                    print(f"Nie znaleziono moda o nazwie '{target_mod}'.")
            except Exception as e:
                print(f"Błąd podczas odinstalowywania moda '{target_mod}': {e}")
        elif action == "exit":
            continue
        else:
            print("Nieznana opcja. Dostępne: list, enable, disable, uninstall, install, exit.")

    # 3. WBUDOWANE
    elif command_lower == "exit":
        stop()

    elif command_lower == "help":
        val = input("Podaj numer strony (1): ")
        page = int(val) if val.isdigit() else 1
        help.help(page)

    elif command_lower == "about":
        info.info()

    elif command_lower == "clear":
        clear()

    elif command_lower == "cd":
        cel = input(r"Ścieżka (lub ..): ")
        try:
            os.chdir(cel)
            logging.info(f"CD -> {os.getcwd()}")
        except Exception as e:
            print(f"Błąd: {e}")

    elif command_lower == "ls":
        cel = input(r"Ścieżka (Enter dla obecnej): ")
        target = cel if cel else current_directory
        try:
            for item in os.listdir(target):
                print(f" - {item}")
        except Exception as e:
            print(f"Błąd: {e}")

    elif command_lower == "pwd":
        print(current_directory)

    elif command_lower == "status":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        stat = input("Status (on/off): ")
        try:
            with open('config.txt', 'w', encoding='utf-8') as f:
                f.write(f"started = {'true' if stat=='on' else 'false'}\n")
                if len(lines) > 1: f.writelines(lines[1:])
            print(f"Status: {stat}")
        except Exception: pass
    elif command.strip() == "config":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        os.system("notepad config.txt")
    elif command.strip() == "update":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        updater.main()
    elif command_lower == "reset":
        
        os.system('cls')

        reset.main()
        
        try:
            os.system("cd C:\\py")
            os.system("py PyCMD.py")
            exit()
            
        except Exception as e:
            print(f"Błąd podczas resetowania: {e}")

    elif command_lower == "github":
        print("Odwiedź moją stronę na GitHub: https://github.com/gametime852")
        print("Lub przejdź bezpośrednio do repozytorium: https://github.com/gametime852/pycmd")
    elif command_lower == "cmd":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        adm_command = input("Polecenie systemowe do wykonania: ")
        try:
            os.system(adm_command)
        except Exception as e:
            print(f"Błąd podczas wykonywania polecenia: {e}")
    elif command_lower == "pycmd":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        os.system("pycmd")
    elif command_lower == "admin":
        if root:
            print("Jesteś zalogowany jako Root. Nie możesz przełączać się na konto administratora.")
            continue
        if admin:
            print("Wylogowano z konta administratora.")
            time.sleep(1)
            admin = False
            clear()
            info.info()
            continue
        login = Prompt.ask("Login")
        haslo = stdiomask.getpass("Hasło: ")
        if login == admin_login and haslo == admin_haslo:
            clear()
            print("Zalogowano jako administrator!")
            print("Dostępne polecenia administratora: help na stronie nr. 2")
            admin = True
        else:
            print("Nieprawidłowy login lub hasło.")
    elif command_lower == "changepass":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        zmien_dane()
    elif command_lower == "changeprefix":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        zmien_prefix()
    elif command_lower == "fabric":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        from modules import fabric
        fabric.main()
    elif command_lower == "crash":
        if not admin:
            print("Nie masz uprawnień administratora.")
            continue
        raise TestCrash()
    elif command.strip() == "root":
        
        if root:
            print("Wylogowano z konta root.")
            time.sleep(1)
            root = False
            admin = False
            clear()
            info.info()
            continue
        # Zamiast hasha, podajemy publiczny link do odczytu z Twojej bazy Firebase
        FIREBASE_URL = "https://pycmd-e8afa-default-rtdb.europe-west1.firebasedatabase.app/root.json"

        class BladUprawnien(Exception):
            def __init__(self, wiadomosc="Odmowa dostępu! Błędny kod uprawnień root."):
                self.message = wiadomosc
                super().__init__(self.message)

        def pobierz_aktualny_hash():
            try:
                response = requests.get(FIREBASE_URL, timeout=5)
                
                response.raise_for_status() 
                dane = response.json()
                
                # Jeśli dane to None (baza jest pusta), zapobiegnie to błędom
                if not dane:
                    return None
                    
                return dane.get("code")
                
            except Exception as e:
                print(f"Szczegóły błędu połączenia: {e}")
                return None

        def sprawdz_uprawnienia_root(wprowadzony_kod: str):
            zapisany_hash = pobierz_aktualny_hash()
            
            if not zapisany_hash:
                raise BladUprawnien("Serwer autoryzacji jest niedostępny.")

            wprowadzony_hash = hashlib.sha256(wprowadzony_kod.encode()).hexdigest()
            
            if wprowadzony_hash != zapisany_hash:
                raise BladUprawnien()
            
            return True

        # --- UŻYCIE ---
        try:
            with console.status("Łączenie z serwerem...",spinner="dots", spinner_style="white"):
                # Tutaj umieść swój kod, który zajmuje czas
                time.sleep(1)
            kod_od_uzytkownika = stdiomask.getpass("Podaj kod autoryzacji root: ")
            
            sprawdz_uprawnienia_root(kod_od_uzytkownika)
            
            clear()
            admin = True
            root = True

            print("Zalogowano jako Root!")

        except BladUprawnien as e:
            print(f"BŁĄD: {e}")
    else:
        if command.strip():
            print(f"Nieznane polecenie: {command}")
            logging.warning(f"Nieznane polecenie: {command}")
