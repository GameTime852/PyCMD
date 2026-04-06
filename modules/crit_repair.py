from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
import time

def main():

    console = Console()

    # Konfigurujemy białe style dla paska i procentów
    with Progress(
        TextColumn("[#00B8A8]{task.description}"), # Pomarańczowy opis
        BarColumn(
            style="grey37",              # Kolor "tła" paska
            complete_style="#00B8A8",      # Kolor wypełnienia paska
            finished_style="bold #00FFEA"  # Kolor paska po zakończeniu
        ),
        
        TaskProgressColumn(text_format="[bold #00D6C4]{task.percentage:>3.0f}%"), # Pomarańczowe procenty
        console=console
    ) as progress:
        
        task = progress.add_task("Naprawiam system...", total=100)
        
        while not progress.finished:
            time.sleep(0.02)
            progress.update(task, advance=1)
