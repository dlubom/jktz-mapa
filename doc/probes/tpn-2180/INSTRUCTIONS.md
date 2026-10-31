# Odrzucalne sondy przeglądarki

To materiał badawczy, nie początek pełnej aplikacji. Sonda TPN została
osobno zatwierdzona i opublikowana na Pages; brak produkcyjnego workflow danych.
Wyniki i ograniczenia: [raport](../../PAGES_BROWSER_PROBE.md).

## Statyczna sonda TPN

W tym katalogu (Node 22.12+ lub nowszy zgodny z Vite):

```sh
npm ci --ignore-scripts
npm run build
python3 -m http.server 8765 --bind 127.0.0.1 --directory dist
```

Otwórz `http://127.0.0.1:8765/`. Domyślnie OSM jest wyłączony, aby nie
maskować błędu TPN. Włącz go do próby fallbacku. Kontrole negatywne:
`?mode=xyz-cors`, `?mode=data`. Wybór warstwy także przez `?dataset=NMT`.
Sonda nie ma proxy. Zamknij serwer przez Ctrl-C.

Publiczna sonda: `https://dlubom.github.io/jktz-mapa/`. Do ponowienia
pomiarów publicznych użyto kopii `browser-probe.js` i `browser-scenarios.js`
z adresem `http://127.0.0.1:8765/` zastąpionym tym publicznym URL
i oddzielnym katalogiem zrzutów. Wyniki są w `evidence/pages/`.
W CLI wybiera się silnik przez `open <URL> --browser firefox|webkit|chrome`.

`browser-probe.js` i `browser-scenarios.js` są callbackami Playwright CLI
`run-code --filename <plik>`. Przed ich uruchomieniem utwórz
`/private/tmp/jktz-tpn-evidence` i otwórz sesję przeglądarki. Pierwszy plik
mierzy cztery podkłady, DPR i negatywne kontrole; drugi luki, wymuszoną
awarię żądań TPN, ręczny powrót, skale i obrót. Wymagają Chromium dla
porównania z zapisanym wynikiem. Nie wyłączają zabezpieczeń CORS.

## Osobna, lokalna sonda rastrów

Najpierw uruchom [generator próbek](../inputs-rasters/) i zachowaj jego
`rasters`, `pyramid-512-progress.jsonl`, `preview-512.json`. Python wymaga
GDAL z WebP; ścieżka wejść jest argumentem, nie sąsiednim checkoutem.

```sh
npx vite build --config vite.raster.config.js
python3 prepare-raster-samples.py /private/tmp/jktz-input-probe
python3 -m http.server 8766 --bind 127.0.0.1 --directory dist-raster
```

Otwórz `http://127.0.0.1:8766/raster.html?id=001197&mode=tiles`.
Parametry: `mode=preview|tiles`, `resolution=0.25`, `id` jednego z pięciu
planów próbki. `browser-rasters.js` wykonuje 20 przypadków przez Playwright
CLI, używając CDP do profilu sieci — wymaga Chromium. Zrzuty i JSON należy
zachować oddzielnie. Domyślny build TPN nie zawiera rastrów ani tej strony.

`dist`, `dist-raster`, `node_modules` są ignorowane. Można je usunąć po
zakończeniu próby. Skrypty nie są zatwierdzonymi modułami produkcyjnymi.
