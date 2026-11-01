# Procesy i cache rastrów

Plany generują domyślnie najwyżej 4 procesy. Każdy otwiera własne dane GDAL;
metadane i relacje powstają w kolejności źródłowego manifestu.

```sh
# Jeden proces, bez cache rastrów:
python scripts/pipeline.py build --lock .build/inputs.json --workers 1

# Procesy i lokalny cache:
python scripts/pipeline.py build --lock .build/inputs.json --workers 4 --raster-cache .build/rasters
```

Cache obejmuje WebP i pliki georeferencji PAM. Klucz uwzględnia źródło,
kod renderowania i wersje bibliotek. Pełny inwentarz i SHA-256 są sprawdzane
przed użyciem; niekompletny lub uszkodzony wpis jest regenerowany.
Metadane i przypięcia bieżącego wykonania powstają od nowa.

CI i publikacja korzystają z cache automatycznie. Brak `--raster-cache`
wyłącza go lokalnie; usunięcie `.build/rasters` wymusza regenerację.
Nowy Run nadal sprawdza Latest, produkcyjny Re-run zachowuje swoje przypięcia.
Wybrany PR w osobnym repozytorium podglądu korzysta z procesów bez wspólnego
cache między kandydatami. Cache nie zastępuje paczek rollbacku.
