# Raster performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Skrócić budowę przez cache WebP i najwyżej cztery procesy bez zmiany wyników.
**Architecture:** `pipeline.py` zachowuje import i walidację metadanych, wydziela render jednego planu. `raster_cache.py` odpowiada za tożsamość i walidację cache. Wspólna akcja Actions buduje dane i obsługuje repozytoryjny cache.
**Tech Stack:** Python 3.12+, GDAL, ProcessPoolExecutor/spawn, GitHub Actions cache v4.
**Spec:** `docs/superpowers/specs/2026-11-01-raster-performance.md`.

## Global Constraints

- Nie zmieniać parametrów renderowania ani źródeł; pliki WebP identyczne bajtowo.
- Zachować pełny katalog, walidacje, kolejność, atomową podmianę i testy.
- Nowy Run: Latest; produkcyjny Re-run: dotychczasowe przypięcia.
- Gałąź i PR; bez merge, produkcyjnego deployu i zmian pages-state.

## Review Focus

- Niepełny/uszkodzony cache nie może dać częściowego katalogu.
- Symlink i niebezpieczna ścieżka cache nie mogą zmienić plików poza stagingiem.
- Nowa data rozwiązania źródeł ma dać trafienie, nowy TIFF/kod/biblioteka — nietrafienie.
- Procesy kończące w różnej kolejności muszą zachować porządek katalogu/relacji.
- Niezaufany wybrany PR nie może zapisać cache do zaufanego scope main podglądu.

### Task 1: Cache i niezależny render planów

**Files:** `scripts/pipeline.py`, nowy `scripts/raster_cache.py`, nowy `tests/test_rasters.py`.
**Interfaces:** `build(lock, cache, output, *, workers=None, raster_cache=None)`;
`raster_key(lock)`; CLI `cache-key`, `build --workers N --raster-cache PATH`.

- [ ] Napisać realne testy GDAL na małych obróconych rastrach: 1/2 procesy,
  ciepły cache bez renderowania, uszkodzenie/brak/dodatkowy plik i symlink,
  brak poziomów, deterministyczna kolejność i błąd pracownika.
- [ ] Uruchomić testy i potwierdzić oczekiwaną czerwień.
- [ ] Wydzielić render oraz cache z kontrolą pełnych oczekiwanych ścieżek,
  inwentarza i sum; oddzielić dane graficzne od bieżących metadanych.
- [ ] Dodać ograniczone procesy spawn; scalić wyniki według oryginalnego indeksu.
- [ ] Uruchomić nowe testy i cały zestaw Python/TypeScript; commit.

### Task 2: CI, pełna równoważność i dokumentacja

**Files:** nowa `.github/actions/data/action.yml`, workflow CI/Pages,
nowy `scripts/verify_rasters.py`, `tests/test_rasters.py`, `docs/BUILD_PERFORMANCE.md`.
**Interfaces:** akcja `data` przyjmuje lock oraz `save-cache`; opcjonalny
`workflow_dispatch.verify-equivalence` w istniejącym Map checks.

- [ ] Napisać test porównywarki: wykrywa inny obraz, metadane i brak pliku,
  akceptuje wyłącznie zmienną telemetrię raportu.
- [ ] Potwierdzić czerwień, wdrożyć porównywarkę i tryb pełnego testu z
  przypiętą poprzednią wersją pipeline; zachować artefakt dowodu.
- [ ] Dodać dokładny restore/save Actions i budowę nawet przy cache miss.
  Preview template bez zmian: procesy przez zgodny stary CLI, bez współdzielonego
  cache między niezaufanymi kandydatami. Zachować warunki reuse produkcji.
- [ ] Udokumentować klucz, invalidację, procesy i odtwarzanie testu.
- [ ] Zielony zestaw lokalny, niezależne review, commit i PR.

### Task 3: Odbiór PR

- [ ] Poczekać na pełny `map` i ponowić ten sam PR, aby sprawdzić trafienie cache.
- [ ] Uruchomić pełne porównanie starego/zimnego/ciepłego builda na Ubuntu.
- [ ] Pobrać kompletny ZIP; zweryfikować tożsamość, sumy i katalog.
- [ ] Zaktualizować opis PR o rzeczywiste czasy i dowody. Zgłosić gotowość;
  nie scalać. Szablon podglądu dostarczyć osobnym PR, jeśli wymaga synchronizacji.
