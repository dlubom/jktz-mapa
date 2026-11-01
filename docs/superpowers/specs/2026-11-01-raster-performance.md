# Szybsza budowa rastrów

Użytkownik zatwierdził implementację po rozpoznaniu czasów CI: 15–19 minut
generowania 814 planów i 35 031 kafelków. Zakres: cache rastrów i procesy
przetwarzające niezależne plany; pełne testy przeglądarek pozostają obecne.
Dostawa przez PR, bez scalania ani publikacji produkcji.

## Zachowanie

- Zachować EPSG:2180, geometrię, poziomy, margines 1, bilinear, RGBA,
  LOSSLESS=YES i METHOD=4. Pliki obrazów mają być identyczne bajtowo.
- Zachować walidację źródeł, kolejność planów i relacji oraz atomową
  podmianę kompletnego katalogu. Błąd pracownika zatrzymuje build.
- Procesy `spawn`, własne dataset-y; domyślnie najwyżej 4, możliwość `--workers 1`.
- Cache obejmuje WebP i generowane przez GDAL pliki PAM podglądów,
  z pełnym inwentarzem, rozmiarami i SHA-256.
  Brak, uszkodzenie, symlink, niezgodny klucz lub niepełny zestaw powoduje
  regenerację. Nie odtwarzać starych metadanych ani locka.
- Klucz obejmuje źródło Georeferencera, profil, kod przetwarzania i środowisko
  natywnych bibliotek. Pomija `resolvedAt` i SHA commitu samego interfejsu.
- Nowy Run nadal sprawdza Latest; produkcyjny Re-run używa zapisanych przypięć.
- Cache Actions jest dodatkiem: brak usługi lub wpisu nie zatrzymuje builda.
  PR może zapisać cache tylko we własnym merge-ref. Wybrany PR uruchamiany
  przez workflow repozytorium podglądu nie zapisuje cache z niezaufanego kodu.
- Szablon podglądu pozostaje kompatybilny ze starszymi PR: dotychczasowe
  wywołanie build korzysta automatycznie z procesów, bez współdzielonego cache
  między niezaufanymi wybranymi PR. Nie wymaga synchronizacji drugiego repozytorium.

## Odbiór

Jednostkowe przypadki zimnego/ciepłego/uszkodzonego cache, zmiany tożsamości
i awarii pracownika; realne GDAL i identyczność plików przy 1/2 procesach.
Pełne porównanie starego, nowego zimnego i nowego ciepłego builda w Ubuntu
na tym samym locku, z pominięciem wyłącznie czasu/rozmiaru raportu builda.
Wszystkie dotychczasowe testy, 3 silniki × desktop/mobile i weryfikacja ZIP.
Przed zgłoszeniem gotowości: niezależne review, terminalne zielone CI na
dokładnym SHA PR i odczyt pobranego artefaktu. Zmierzyć zimny i ciepły CI.
