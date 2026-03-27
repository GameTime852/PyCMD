import rich
import os
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from modules import load_first
 
console = Console()
 
def main():
    # Wyświetlenie animacji powitalnej
    load_first.load_first()
    
    console.clear()
    console.print(Panel.fit(
        "[bold bright_green]Witaj w Kreatorze Pierwszego Uruchomienia PyCMD![/bold bright_green]\n"
        "[white]Skonfiguruj swoje konto administratora, aby zabezpieczyć dostęp do systemu.[/white]",
        border_style="bright_blue"
    ))

    # Pobieranie danych od użytkownika
    admin_login = Prompt.ask("[cyan]Ustal login administratora[/cyan]")
    admin_password = Prompt.ask("[cyan]Ustal hasło administratora[/cyan]", password=True)
    
    # Ścieżka do pliku config.txt w folderze nadrzędnym
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.txt")

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf8') as f:
                lines = f.readlines()
            
            # Zapewnienie, że mamy odpowiednią liczbę linii w configu
            while len(lines) < 5:
                lines.append("\n")

            # Aktualizacja linii (zakładając strukturę z PyCMD.py)
            lines[3] = f"admin_login = {admin_login}\n"
            lines[4] = f"admin_haslo = {admin_password}\n"

            with open(config_path, 'w', encoding='utf8') as f:
                f.writelines(lines)
            
            console.print("\n[bold green]✅ Konfiguracja zapisana pomyślnie![/bold green]")
        else:
            console.print("\n[bold red]❌ Błąd: Nie znaleziono pliku config.txt![/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Wystąpił błąd podczas zapisu: {e}[/bold red]")