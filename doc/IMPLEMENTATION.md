# Pierwsza kompletna mapa — realizacja i uruchomienie

Kontrakt: [PAGES_MAP_SPEC.md](PAGES_MAP_SPEC.md). Implementacja jest
upoważniona; zmiana działających publicznych Pages wymaga osobnej zgody.
Pracujemy w `jktz-mapa`, bez zmian README, 3D ani repozytoriów źródłowych.

## Etapy

1. Domknięcie specyfikacji: zachowanie uzgodnień, wybór WebP 512,
   zachowanie „Pokaż cały plan”, jawne stany interfejsu i kryteria odbioru.
2. Pipeline pełnego katalogu: Latest → niezmienne przypięcia → pobranie
   i kontrola sum → obiekty, historia, jawne relacje, modele i rastry.
3. Aplikacja: OpenLayers w EPSG:2180, podkłady, polski interfejs,
   wyszukiwanie i szczegóły, warstwy, wybór/nakładanie planów i zasoby.
4. Dostarczenie: testy, statyczny build pod prefiksem Pages, przeglądarki,
   podgląd i paczka do zatwierdzenia; prosty workflow publikacji/rollbacku.

Przekrojowe sprawdzenia obejmują wspólne lokalne ID pomiarów różnych
obiektów, brak relacji, opóźnione odpowiedzi po zmianie wyboru, warianty
planów oraz utratę/powrót podkładu. Są to zachowania produktu, nie nowy
audyt danych źródłowych. Wyniki wykonania należy czytać w raporcie
przekazania, osobno od poniższych poleceń i planu.

Wykonane sprawdzenia, liczebności pełnego katalogu i pozostały odbiór
urządzeń: [ACCEPTANCE.md](ACCEPTANCE.md).

## Granice danych i aplikacji

Pipeline: `scripts/pipeline.py`, zależności `requirements-data.txt`.
Publiczne dane pod `public/data/`; Vite kopiuje je do statycznego buildu.
JSON ma `schemaVersion: 1`, współrzędne `EPSG:2180` w porządku
`[easting, northing]`. Oryginalne wartości zachowane w szczegółach.

| Plik | Zawartość i użycie |
| --- | --- |
| `catalog.json` | `sources`, `counts`, `extent`, indeksy `objects`, `caves`, `models`, `plans`; start i wyszukiwanie |
| `objects/<id>.json` | Wszystkie dostępne pomiary, Best, źródłowe pola i jawne relacje; na żądanie |
| `caves/<id>.json` | Źródłowy rekord jaskini, `externalRefs` i `objectIds`; również jaskinie bez powiązanego obiektu |
| `measurements.geojson`, `differences.geojson` | Pomiary i poziome różnice do Best; GeoJSON w zadeklarowanym EPSG:2180 |
| `models/<id>.geojson` | Model JKTZ z zachowanym Z, bez duplikowania eksportu zbiorczego |
| `plans/<id>/details.json` | Źródłowe metadane planu, affine, orientacja i pochodzenie |
| Podglądy/kafle planów | Ścieżki z indeksu planu, bez odgadywania nazw plików |

Obiekt indeksu ma `id`, `name`, `caveId`, `caveName`, `systemName`,
`coordinate`, `searchText`, `best`, `detailUrl`, `modelIds`, `planIds`.
Jaskinia indeksu ma `id`, `name`, `systemName`, `objectIds`, `searchText`
i `detailUrl`. Rekord bez obiektu pozostaje wyszukiwalny, bez tworzenia
fikcyjnego punktu. Model ma `id`, `name`, `extent`, `objectIds`, `url`,
`featureCount`.
Plan ma `id`, `name`, `extent`, `nativeResolution`, `objectIds`,
`sourceCaveId`, `preview`, `levels`, `tileSize`, `gutter`, `tileUrl`, `detailUrl`
i `orientationStatus`. Podgląd opisuje URL, wymiary i zasięg; poziom
kafli rozdzielczość, wymiary, liczbę kolumn/wierszy, początek siatki
i zasięg. `sourceCaveId` pochodzi wyłącznie z jawnego pola metadanych;
w przeciwnym razie ma wartość `null`. Kafel ma wnętrze 512×512 px i
jednopikselowy gutter: plik 514×514 px, także na brzegu (dopełnienie alfą).
Renderer pomija gutter w zasięgu rysowanej komórki. Brak relacji nie usuwa
planu lub modelu z katalogu. Źródła zawierają dostępne `licenses`
(`name`, przypięty `url`, `text`), bez dziedziczenia licencji przez plany.

Interfejs: zakładki „Obiekt”, „Warstwy”, „Plany”, „Źródła”, globalne
wyszukiwanie obiektów i jaskiń oraz osobny filtr pełnego katalogu planów.
Na małym ekranie obszar mapy kończy się nad panelem; zmiana jego rozmiaru
aktualizuje OpenLayers. Menedżer
obrazów ma wspólny cache LRU, limit sześciu pobrań i anulowanie zbędnych
żądań. Renderer planów korzysta z Canvas/ImageCanvasSource oraz
ImageBitmap; TPN zachowuje sprawdzoną ścieżkę XYZ/TileImage.

## Uruchomienie ze świeżego klonu

Wymagane: Node.js 22 z obsługą TypeScript strip-types, Python ≥3.12,
GDAL z PROJ, NumPy i sterownikiem WebP oraz dostęp do GitHub API/release.
Zależności JS są w `package-lock.json`. CI używa Ubuntu 24.04 oraz
GDAL/NumPy z pakietów systemowych i zapisuje faktyczne wersje; nie
zakładamy identycznych bajtów rastrów między różnymi wersjami GDAL.
Lokalnie używamy interpretera z działającym GDAL (na maszynie wdrożeniowej
`/opt/homebrew/bin/python3`). Nie potrzeba QGIS ani sąsiednich
checkoutów. GitHub token, jeżeli potrzebny do limitów API, pozostaje
zmienną środowiska i nie trafia do plików strony.

```sh
npm ci
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install -r requirements-data.txt
python3 scripts/pipeline.py resolve --lock .build/inputs.json
python3 scripts/pipeline.py fetch --lock .build/inputs.json --cache .build/inputs
python3 scripts/pipeline.py build --lock .build/inputs.json --cache .build/inputs --output public/data
python3 -m unittest discover -s tests -p 'test_*.py'
npm test
npm run build
npm run preview -- --port 4173
```

Podgląd: `http://127.0.0.1:4173/`. Test przeglądarki:
`npm run test:browser` (Playwright; wymagane zainstalowane silniki).
Weryfikujemy wynik `dist/`, nie tylko dev-server. `.build/`, `public/data/`
i `dist/` są odtwarzalnymi produktami, nie materiałem do historii Git.

## Przygotowana publikacja — po osobnej zgodzie

- `ci.yml`: testy i kontrola buildu, bez deployu.
- `pages.yml`: ręczny Run, pełny pipeline i publikacja. `Re-run` używa
  `inputs-<run_id>` i gotowej paczki, jeśli istnieje; nie odczytuje Latest.
- `pages-rollback.yml`: parametr `package` wskazuje gotowy `pages-<run_id>`,
  `probe-original` (pierwotna sonda) albo `recover` (uzgodnienie potwierdzonego
  ukończonego deployu). Bez Latest i ponownego buildu.
- `scripts/publication.py`: archiwum, ewidencja `pages-state`, warunkowy
  zapis, kolejność operacji i retencja. Paczki mają `make_latest=false`.

Lokalne pakowanie gotowego `dist/`:

```sh
python3 scripts/publication.py package --app-sha <pełny-SHA-commitu> --package-id pages-<liczba>
```

Wynik: `.build/package/site.tar.gz`, `package.json`, `inputs.json`.
W Actions identyfikatorem paczki jest `pages-<run_id>`.

Przed pierwszą publikacją przedstawiamy dokładny commit aplikacji,
przypięcia trzech źródeł, rozmiar i sumę paczki oraz wyniki sprawdzeń.
Po zgodzie: scalenie zatwierdzonego commitu, jednorazowe przełączenie Pages
na Actions (`build_type=workflow`) i dopuszczenie `main` w środowisku
`github-pages`, potem Run workflow. Obecna sonda jest archiwizowana przez
sprawdzony pakiet `original` z technicznego release
`pages-publication-probe-20261031`; bootstrap sprawdza jej publiczne bajty.
Po deployu wymagany jest odczyt publicznego manifestu i smoke test.

Bieżąca paczka nie wygasa, zastąpiona jest chroniona co najmniej 15 dni
od zastąpienia; przypięcia wejść mają 90 dni retencji artefaktu.
Sprzątanie odkłada usuwanie, gdy inne operacje Pages/rollback są
niezakończone. `pending/unknown` chroni obie paczki i zatrzymuje nowe
wdrożenia do rozpoznania. Nie uruchamiamy automatycznego rollbacku.

Fizyczne iPhone/Safari i Android/Chrome oraz niewykonane próby natywnego
Safari/Firefoksa muszą zostać nazwane w raporcie jako pozostałe do odbioru;
emulacja rozmiaru ekranu nie zastępuje telefonu.
