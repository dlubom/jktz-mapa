# Praca nad mapą JKTZ

To statyczna mapa 2D na GitHub Pages, łącząca trzy projekty wymienione
w [README.md](README.md). Interfejs: TypeScript, OpenLayers, proj4 i Vite.
Dane przygotowuje Python z GDAL; aplikacja działa bez backendu i QGIS.

## Gdzie pracować

- `src/` — mapa, polski interfejs, wyszukiwanie i zarządzanie obrazami planów.
- `scripts/pipeline.py` — przypięcie wydań, pobranie i budowa pełnego katalogu.
- `scripts/publication.py`, `.github/` — CI, publikacja i rollback.
- `tests/` — testy danych, publikacji, zasobów i przeglądarek.
- `public/data/`, `dist/`, `.build/`, `output/` — generowane dane, build i wyniki; pozostają poza Git.

## Główne założenia

- Widok naprawdę używa EPSG:2180. Geometria ma kolejność `[easting, northing]`;
  interfejs pokazuje X jako północ i Y jako wschód.
- Zachowuj źródłowe współrzędne, Z, metadane, niepewności i jawne relacje.
  Powiązania wynikają z ID, nie podobieństwa nazw. Pomiar identyfikuje para `(object_id, id)`.
  Mapa nie poprawia źródeł ani nie przesuwa planów do pozycji Best.
- Początkowo: Best z wszystkimi nazwami, ciągi JKTZ i plany włączone;
  pozostałe/odrzucone pomiary i różnice wyłączone. Podkład TPN 2020, zapasowo OSM.
  TPN korzysta z XYZ/Canvas bez `crossOrigin`; sprawdzaj jego działanie także na Pages.
- Plany mają domyślnie 75% krycia i ładują się według skali oraz widoku.
  „Pokaż cały plan” ładuje lekki podgląd; przybliżenie daje szczegóły.
  Zachowuj kolejność nakładania, anulowanie zbędnych pobrań i zwalnianie bitmap.
- Build obejmuje pełne katalogi z wydań źródłowych; nie wymaga sąsiednich checkoutów.
  Pracuj w tym repozytorium; istniejące projekty 3D i źródłowe są osobne.

## Uruchomienie i sprawdzenia

Potrzebne: Node.js 22.14+, Python 3.12+, GDAL/PROJ z WebP, NumPy,
`curl` i GitHub CLI `gh` z dostępem do API (`gh auth login` lub `GH_TOKEN`).
Środowisko referencyjne CI: Ubuntu 24.04; instalacja w `.github/actions/setup/action.yml`.

```sh
npm ci
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install -r requirements-data.txt
# resolve wykonaj raz dla nowej migawki; zachowaj istniejące przypięcia
python scripts/pipeline.py resolve --lock .build/inputs.json
python scripts/pipeline.py fetch --lock .build/inputs.json --cache .build/inputs
python scripts/pipeline.py build --lock .build/inputs.json --cache .build/inputs --output public/data
npm test
python -m unittest discover -s tests -p 'test_*.py'
npm run build
npm run preview -- --port 4173
```

Podgląd: `http://127.0.0.1:4173/`. Przy zmianach samego interfejsu używaj już
wygenerowanych danych. Test gotowego `dist/`: `npx playwright install chromium firefox webkit`,
następnie `BROWSERS=chromium,firefox,webkit npm run test:browser`.
Sprawdzaj wyszukiwanie, historię, warstwy, cały plan i detal, duży/mały ekran oraz TPN/OSM.
Emulacja ekranu nie zastępuje odbioru na fizycznym telefonie.

## Publikacja

- Publikuj na zlecenie użytkownika: `pages.yml`, ręczny Run na `main`.
  Nowy Run sprawdza Latest wszystkich źródeł; Re-run używa pierwotnych przypięć.
  Nieudany build lub test zatrzymuje publikację.
- `pages-rollback.yml` używa gotowej paczki `pages-<run_id>` z archiwum.
  Ewidencja jest na gałęzi `pages-state`; zachowuj ją i istniejące paczki rollbacku.
  `pending/unknown` wymaga rozpoznania, a nie nadpisania stanu.
- Bieżąca paczka nie wygasa, zastąpiona jest chroniona minimum 15 dni od zastąpienia;
  przypięcia wejść mają 90 dni retencji. Po deployu sprawdź publiczny manifest i mapę.
