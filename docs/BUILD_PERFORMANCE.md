# Budowa danych: procesy i cache rastrów

Generowanie planów używa domyślnie najwyżej czterech procesów `spawn`.
Każdy otwiera własny TIFF/VRT i zapisuje osobny katalog. Metadane i relacje
powstają w procesie głównym, w kolejności źródłowego manifestu.
Parametry geometrii, bilinear, marginesów i WebP pozostają takie same.

```sh
# Bez cache rastrów, jeden proces — przydatne do diagnozy.
python scripts/pipeline.py build --lock .build/inputs.json --workers 1

# Procesy i lokalny cache gotowych rastrów.
python scripts/pipeline.py build --lock .build/inputs.json --workers 4 --raster-cache .build/rasters

# Dokładny klucz używany także przez Actions.
python scripts/pipeline.py cache-key --lock .build/inputs.json
```

Oba warianty używają domyślnie `.build/inputs` i `public/data`.
Katalog cache rastrów musi być oddzielony od wejść i wyjścia.
Brak `--raster-cache` wyłącza ten cache. Usunięcie wyłącznie
`.build/rasters` wymusza ponowne generowanie; nie usuwa przypięć źródeł.

## Co jest przechowywane

Wyłącznie WebP i pliki georeferencji PAM `preview.webp.aux.xml`, gdy PAM
jest włączone. Przed kopiowaniem importer porównuje pełen zestaw ścieżek
wyliczony z bieżącej geometrii oraz rozmiary i SHA-256 zapisane w manifest.json.
Brak pliku, dodatkowy plik, niezgodna suma, symlink lub wadliwy manifest
oznacza cache miss i regenerację. Sprawdzenia źródeł nadal wykonują się w całości.

Klucz obejmuje SHA-256 i rozmiar źródłowego archiwum Georeferencera,
profil, kod `pipeline.py` i `raster_cache.py`, wersje i konfigurację
GDAL/PROJ/libwebp/Pythona, obraz runnera oraz rewizje natywnych pakietów apt.
Nie obejmuje `resolvedAt`, kodu TypeScript/CSS ani SHA commitu całej aplikacji.
Zmiana GPS/JKTZ nie unieważnia niezmienionych rastrów.

Metadane, katalog, relacje, lock, raport budowy i sumy paczki powstają dla
bieżącego wykonania. Nowy Run nadal sprawdza Latest; produkcyjny Re-run
korzysta z dotychczasowego przypięcia. Cache nie zastępuje paczek rollbacku.

## GitHub Actions

Wspólna akcja `.github/actions/data` obsługuje cache w CI i nowej budowie
produkcyjnej. Awaria usługi cache nie blokuje generowania danych.
Cache z domyślnej gałęzi jest dostępny dla PR; wpis zapisany przez zwykły
`pull_request` pozostaje w jego merge-ref i nie zasila produkcji ani innych PR.
Pierwszy przebieg jest zimny, ponowienie tego samego PR może sprawdzić trafienie.
Zmiana kodu renderera unieważnia wcześniejsze wpisy.

Wybrany PR w osobnym repozytorium podglądu korzysta z równoległości przez
dotychczasowe wywołanie CLI, bez współdzielenia cache między niezaufanymi
kandydatami. Nie wymaga aktualizacji publikatora i zachowuje obsługę starszych PR.

## Pełne porównanie

`Map checks` ma opcjonalne ręczne wejście `verify-equivalence=true`.
Po zwykłej budowie pobiera poprzedni importer z przypiętego commitu
`aaae3780372dc55cbcf5268418fff8623f5d4e67` i wykonuje trzy budowy tego samego locka:
poprzednią, nową z zimnym cache i nową z ciepłym cache.

Porównuje wszystkie ścieżki i bajty, w tym WebP/PAM/metadane. Jedyny wyjątek
to pola `buildSeconds` i `bytes` w `build-report.json`: czas jest zmienny,
a liczba jego cyfr zmienia rozmiar raportu. Pozostałe pola raportu też są porównywane.
Zmiana danych, kolejności tablic lub choćby jednego obrazu zatrzymuje test.
Wyniki, logi i przypięcia trafiają na 15 dni do artefaktu `raster-equivalence-*`.
Ten kosztowny test jest ręczny, żeby następne zwykłe PR nie powielały pełnej
budowy referencyjnej. Wszystkie dotychczasowe testy i kompletny ZIP pozostają.

Lokalnie, z zapisaną kopią poprzedniego importera:

```sh
python scripts/verify_rasters.py --reference-script .build/reference-pipeline.py --lock .build/inputs.json
```

Wymaga świeżego `.build/equivalence`. Czasy i logi są w
`output/raster-equivalence`; pełne katalogi porównania pozostają w `.build/equivalence`.
