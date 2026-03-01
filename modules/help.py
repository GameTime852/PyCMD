def help(page=1):

    if page == 1:
        print(f"Strona {page}")
        print("Dostępne polecenia:")
        print("  help  - Wyświetla tę pomoc")
        print("  about - Informacje o PyCMD")
        print("  clear - Czyści ekran")
        print("  cd    - Zmienia bieżący katalog")
        print("  ls    - Wyświetla zawartość katalogu")
        print("  exit  - Zamyka PyCMD")
        print("  pwd   - Wyświetla bieżący katalog")
        print("  update - Sprawdza aktualizacje PyCMD")
        print("  getmods - Otwiera ekran pobierania modów")