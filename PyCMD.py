import os
import time
import importlib.util
import sys
import logging
import json  # <--- Konieczne do zapisu configu modów
import atexit
from pathlib import Path

# import modules.help as help
# import modules.info as info
# import modules.Start as Start
# import modules.load_exit2 as load_exit2
# import modules.celebration as celebration

from modules import getmods, help, info, Start, load_exit2, celebration, updater, reset

def stop():
    logging.info("Zamykanie...")
    clear()
    load_exit2.load_exit()
    try:
        with open('config.txt', 'w', encoding='utf-8') as f:
            f.writelines(["started = false\n"] + lines[1:])
    except: pass
    exit()
# first_file = Path("first")
# if first_file.exists() and first_file.is_file():
#     celebration.celebrate()
#     first_file.unlink(missing_ok=True)


# --- KONFIGURACJA LOGÓW ---
logging.basicConfig(
    filename='logs.txt',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
    filemode='w',
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

if not started == "started = true\n":
    Start.start()
    with open('config.txt', 'w', encoding='utf-8') as f:
        f.writelines(["started = true\n"] + lines[1:])


# --- PĘTLA GŁÓWNA ---

while True: 
    print("")
    current_directory = os.getcwd()
    try:
        command = input(prefix + " " + current_directory + "> ")
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
        action = input("Opcja (list/enable/disable): ").strip().lower()
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
        
        else:
            print("Nieznana opcja. Dostępne: list, enable, disable")

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
        stat = input("Status (on/off): ")
        try:
            with open('config.txt', 'w', encoding='utf-8') as f:
                f.write(f"started = {'true' if stat=='on' else 'false'}\n")
                if len(lines) > 1: f.writelines(lines[1:])
            print(f"Status: {stat}")
        except Exception: pass
    elif command.strip() == "config":
        os.system("notepad config.txt")
    elif command.strip() == "update":
        updater.main()
    elif command.strip() == "getmods":
        getmods.main()
    elif command_lower == "reset":
        
        os.system('cls')

        reset.main()
        
        try:
            os.system("cd C:\\py")
            os.system("py PyCMD.py")
            exit()
            
        except Exception as e:
            print(f"Błąd podczas resetowania: {e}")


    else:
        if command.strip():
            print(f"Nieznane polecenie: {command}")
            logging.warning(f"Nieznane polecenie: {command}")