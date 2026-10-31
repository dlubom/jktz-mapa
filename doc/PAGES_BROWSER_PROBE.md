# Próby przeglądarki: lokalnie i na Pages — 2026-10-31

**Wynik:** bezpośredni TPN działa w EPSG:2180 przez `XYZ`/`TileImage`/
Canvas2D w badanym Chromium. Pięć planów wyświetlono jako podglądy i kafle
w rzeczywistym OpenLayers. Poniższa pierwsza część opisuje próbę lokalną;
publiczne Pages sprawdzono po osobnej zgodzie w sekcji na końcu dokumentu.
Nie jest to odbiór telefonu ani aplikacji.

## Warunki i dowody

macOS 27.0.1 arm64, Chromium 156.0.8078.74, OpenLayers 10.11.0,
proj4 2.22.0, Vite 8.3.5. Wersje pakietów przypięte lockfile.
Zbudowane pliki statyczne podawał `python -m http.server` na localhost;
bez proxy, service workera, COOP/COEP i QGIS. Nowy kontekst przeglądarki
dla każdego przypadku. To test silnika desktopowego; DPR 3 nie emuluje
pamięci, CPU, Safari ani sprzętu iPhone'a.

Odrzucalny kod: [próba](probes/tpn-2180/INSTRUCTIONS.md).
Surowe wyniki: [TPN](probes/tpn-2180/evidence/browser-results.json),
[awarie i skale](probes/tpn-2180/evidence/scenarios.json),
[rastry](probes/tpn-2180/evidence/rasters.json).
Zrzuty oglądano lokalnie w `/private/tmp/jktz-tpn-evidence/`;
ten katalog jest tymczasowy, a zachowane skrypty pozwalają ponowić próbę.

## TPN — dowód renderowania, nie tylko HTTP

Widok ma `projection=EPSG:2180`, źródło `EPSG:3857`, `crossOrigin`
nieustawione. `OSM` wyłączono w próbach pozytywnych, aby nie maskowało
braku TPN. Przy 1 m/px CSS i obszarze mapy 1200×602 px:

| Podkład | Kafle załadowane/błędne | Wynik oględzin |
| --- | ---: | --- |
| RGB 2020 | 43 / 0 | Ortofotomapa narysowana |
| RGB 2018 | 43 / 0 | Ortofotomapa narysowana |
| NMT | 43 / 0 | Obraz modelu narysowany |
| NMPT | 43 / 0 | Obraz modelu narysowany |

Nie było błędów wykonania JS. Żądania szły bezpośrednio do TPN jako obrazy,
odpowiedzi 200 nadal nie zawierały ACAO/CORP. `rendercomplete` połączono
z licznikami kafli i oględzinami obrazu; samo zdarzenie nie jest dowodem,
bo wystąpiło także w kontrolach, w których wszystkie kafle zawiodły.

RGB 2020 przy viewport 393×852, DPR 3: 20/20 kafli, płótno 1179×1788 px,
poprawny obraz. Źródło nadal pobierało poziom 17, podobnie jak przy DPR 1.
**Większe płótno samo nie gwarantuje większej szczegółowości źródła.**
Nie zmieniano źródłowej georeferencji. Środek próbki obliczony niezależnie
przez GDAL/PROJ: easting 571469,341063524, northing 156352,478018015;
wynik proj4 w przeglądarce zgodny z dokładnością lepszą niż 10⁻⁸ m.
To kontrola transformacji punktu, nie geodezyjna ocena ortofotomapy.

Kontrole negatywne tego samego widoku:

- `XYZ` z `crossOrigin='anonymous'`: 0/43 kafli, blokada CORS.
- `ol/source/ImageTile` (DataTile, domyślny CORS): 0/43 kafli.
- Celowy odczyt `getImageData` po poprawnym narysowaniu `XYZ`:
  oczekiwany `SecurityError`. To oddzielna kontrola właściwości płótna,
  a nie błąd ścieżki wyświetlania.

Zachowujemy więc konkretną ścieżkę `XYZ`, bez eksportu/odczytu pikseli TPN.
Jest zgodna z [mechanizmem reprojekcji OpenLayers](https://openlayers.org/doc/tutorials/raster-reprojection.html)
i sprawdzonym [kodem 10.11.0](https://github.com/openlayers/openlayers/blob/v10.11.0/src/ol/reproj.js).
Zmiana na DataTile/WebGL wymaga osobnego dowodu.

## Awarie, skale i powrót

Druga seria używała viewportu 1000×760, DPR 1. W próbie luk NMT
wycentrowanej na źródłowym `17/72806/44888` nie wczytało się 35/35 kafli;
widoczny pozostał OSM i komunikat. To stan tego widoku, nie diagnoza
awarii całej usługi. Kontrolowane zerwanie wyłącznie żądań TPN spowodowało
25 błędów i pozostawiło OSM. Po usunięciu blokady i „Spróbuj ponownie”
załadowało się 25/25 kafli, komunikat zniknął.

Dodatkowo zablokowano dokładnie jeden URL RGB 2020: 24 kafle poprawne,
1 błędny. Zrzut potwierdził OSM w lokalnej luce oraz TPN wokół niej,
bez globalnego przełączenia podkładu.

RGB 2020 narysowano też przy 4 m/px CSS (40 kafli poziomu źródła 15),
0,07 m/px (12 kafli poziomu 20) oraz obrocie widoku 20° i kryciu 50%
(33 kafle). Oględziny nie wykazały oczywistych przerw w tych próbkach;
nie jest to ilościowy test wszystkich granic kafli i pokrycia.

Sonda ma tylko ręczne ponowienie; nie realizuje jeszcze docelowych
ograniczonych automatycznych prób, wygaszania komunikatów ani kontroli
pełnego cyklu powrotu sieci. Liczniki ignorują zdarzenia poprzedniego
źródła po przełączeniu. Nie wprowadza nowego kontraktu UI.

## Podglądy i szczegóły planów

Osobny build lokalny, bez TPN/OSM. Dane pochodzą z
[próby pełnego katalogu](PAGES_INPUTS_RASTERS_PROBE.md).
Pięć planów: Miętusia `001197`, Piwnica Miętusia `001459-pza-2024`,
Juhaska `001212`, `001140`, Kokonowa `010865`. Każdy: podgląd oraz kafle,
DPR 1 i 3 — 20 przypadków, wszystkie zakończyły renderowanie bez błędów.
Po przeglądzie doprecyzowano warunek sukcesu (załadowany obraz, zero
błędów, render), a powtórne [sprawdzenie 20/20 przypadków](probes/tpn-2180/evidence/rasters-verification.json)
potwierdziło wynik. Tabela czasów poniżej opisuje pierwszą serię.
Krycie 75%, białe tło skanu, alfa poza skanem. GDAL uwzględnił pełną
transformację i przygotował north-up EPSG:2180.

Profil: 10 Mb/s, 80 ms, wyłączony cache HTTP, bez ograniczenia CPU,
jedna próba na przypadek. Pomiar od nawigacji do `rendercomplete`,
łącznie z małym kodem sondy i jej indeksem. To wyniki orientacyjne,
bez median/p95 i bez wniosku o czasie gotowości przyszłej aplikacji.

| Miętusia | Obrazy | Treści obrazów | Bufory obrazów RGBA* | Czas próby |
| --- | ---: | ---: | ---: | ---: |
| Cały podgląd 512, DPR 1 | 1 | 19 044 B | 0,58 MiB | 615 ms |
| Cały podgląd 512, DPR 3 | 1 | 19 044 B | 0,58 MiB | 618 ms |
| Szczegół 0,25 m/px CSS, DPR 1 | 8 | 236 934 B | 8 MiB | 850 ms |
| Szczegół 0,25 m/px CSS, DPR 3 | 20 | 333 740 B | 20 MiB | 998 ms |

\* Obliczenie z liczby pikseli, nie RSS. W kaflach obejmuje płótna 512²
z dopełnieniem krawędzi; nie obejmuje dodatkowych kopii dekodera, płótna
widoku, GPU, podkładów i reszty aplikacji. Viewporty DPR 1 i 3 mają różne
rozmiary CSS (1200×800 i 393×852), więc nie jest to izolowany koszt DPR.
JS heap zapisano w JSON jako pomocniczy odczyt, nie całkowitą pamięć.

Podgląd całości Miętusiej pokazuje układ planu; drobne napisy nie są
czytelne. W szczególe DPR 3 czytelne są m.in. „Szmaragdowe Jeziorko”,
„Bliźniacze Salki”, liczby i rysunek. Drobne opisy PZA przy tej samej
skali nadal wymagają dalszego przybliżenia. **Nie ma jednego progu skali
gwarantującego czytelność wszystkich planów.** To zgodne z ustaleniem,
że „Pokaż cały plan” gwarantuje lekki podgląd, nie wszystkie szczegóły.

Sonda kafli dobiera poziom według rozdzielczości CSS/DPR (do rozdzielczości
źródła), używa TileLayer i dopełnia brzegowe kafle alfą do 512², aby ich
nie rozciągać. Nie jest produkcyjnym menedżerem zasobów: nie sprawdza
wielu nakładanych planów, zwalniania cache ani długiej nawigacji. Piramida
nie ma gutterów; odbiór szwów pod obrotem pozostaje niewykonany.

## Publikacja zatwierdzonej próby

Przygotowany domyślny `dist/` zawiera tylko stronę sondy TPN i dwa zasoby
JS/CSS. Wariant rastrów (`dist-raster/`) jest osobny i nie wchodzi do tej
paczki. Manifest plików i sumy:
[publication-candidate.json](probes/tpn-2180/evidence/publication-candidate.json).
Łącznie **389 250 B** plików statycznych (ZIP 118 496 B). Lokalna próba
pod prefiksem `/jktz-mapa/` także wczytała JS/CSS i 43/43 kafle TPN;
nie jest to weryfikacja nagłówków ani działania publicznego hostingu.

Użytkownik odpowiedzią „Ok” zatwierdził włączenie Pages wyłącznie
w `jktz-mapa` i publikację tej sondy. Działa pod
[publicznym adresem](https://dlubom.github.io/jktz-mapa/).
Publiczne są kontrolki czterech podkładów, widok EPSG:2180, krycie,
OSM i liczniki. Brak katalogu jaskiń i pełnej aplikacji. Dane podkładów
pozostają na serwerach TPN/OSM; nie archiwizujemy ich. README bez zmian.
To etap techniczny, bez automatycznego przejścia do budowy aplikacji.

Opublikowano dokładnie trzy pliki paczki plus pusty `.nojekyll`,
zapobiegający przetwarzaniu przez Jekyll. Tymczasowe źródło Pages:
`gh-pages`, katalog `/`, `build_type=legacy`, wymuszony HTTPS.
To metoda dostarczenia odrzucalnej sondy, nie implementacja docelowego
kontraktu Run workflow/Latest/Re-run. W chwili tego deployu `main`
pozostawało na `5a519dc`;
nie zmieniono README ani innych repozytoriów.

Commit publicznej paczki:
[`12a6783bc09eda112f9f187f9df5825264bbf183`](https://github.com/dlubom/jktz-mapa/commit/12a6783bc09eda112f9f187f9df5825264bbf183).
[Wdrożenie 41183308660](https://github.com/dlubom/jktz-mapa/actions/runs/41183308660)
zakończone `completed/success`; Pages `built`.
Trzy pliki pobrane ponownie spod publicznych URL miały zgodne SHA-256
i łączny rozmiar 389 250 B po dekompresji. Odpowiedzi używały HTTP/2,
gzip oraz poprawnych MIME HTML/JS/CSS. Brak nagłówków COOP/COEP.
Nie mylimy sumy plików z transferem całego widoku wraz z podkładami.

Dowody: [odczyt plików i nagłówków](probes/tpn-2180/evidence/pages/public-readback.json),
[wynik workflow](probes/tpn-2180/evidence/pages/deployment-run.json),
[ustawienia Pages](probes/tpn-2180/evidence/pages/pages-settings.json).

Z publicznego HTTPS powtórzono cztery źródła XYZ przy DPR 1,
RGB 2020 przy DPR 3 oraz dwie negatywne kontrole CORS/DataTile.
Każdy przypadek używał nowego kontekstu. OSM było wyłączone w próbach
TPN; zrzuty potwierdziły rzeczywisty obraz, a nie sam HTTP 200.
Dokładne wyniki: [Chromium](probes/tpn-2180/evidence/pages/chromium.json)
i [WebKit](probes/tpn-2180/evidence/pages/webkit.json).

| Silnik desktopowy na macOS | Cztery podkłady DPR 1 | RGB 2020 DPR 3 | Kontrole CORS/DataTile |
| --- | --- | --- | --- |
| Chromium 156.0.8078.74 | Każdy 43/43, bez błędów renderowania | 20/20 | Obie 0/43, oczekiwana blokada |
| Playwright WebKit 26.6 | Każdy 43/43, bez błędów renderowania | 20/20 | Obie 0/43, oczekiwana blokada |

Firefox 156 nie został zaliczony: instalacja silnika zakończyła się,
ale uruchomienie profilu testowego nie powiodło się (`Could not find
profile folder`). Nie uzyskano wyniku renderowania strony. To ograniczenie
lokalnego środowiska testowego, nie dowód niezgodności TPN z Firefoksem;
próba pozostaje do wykonania.

W Chromium [powtórzono też awarie i skale](probes/tpn-2180/evidence/pages/chromium-scenarios.json):
pojedyncza luka 24 sukcesy/1 błąd odsłaniała OSM lokalnie; awaria 0/25,
ręczny powrót 25/25. Sprawdzono poziomy źródła 15/20, obrót 20° i krycie
50%. To weryfikacja sondy bez produkcyjnej polityki automatycznych ponowień.

**Niewykonane:** natywne Safari, rzeczywisty iPhone 14 Pro,
rzeczywisty Android/Chrome, pełna pamięć urządzeń i odbiór pełnej aplikacji.
Playwright WebKit na komputerze nie jest Safari na iPhonie.
Próby docelowego workflow, odzysku ewidencji i rollbacku są osobnym
scenariuszem opisanym w [raporcie publikacji](PAGES_PUBLICATION_RESEARCH.md),
nadal niewykonanym. Pierwszy udany deploy sondy ich nie zalicza.
