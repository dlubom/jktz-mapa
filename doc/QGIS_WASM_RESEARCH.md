# QGIS WebAssembly a statyczna mapa JKTZ

**Uzupełnienie 2026-10-31:** [nowa próba przeglądarki](PAGES_BROWSER_PROBE.md)
potwierdziła renderowanie czterech podkładów TPN w EPSG:2180
przez `XYZ`/Canvas2D, bez proxy: najpierw lokalnie, następnie po osobnej
zgodzie na publicznym Pages. Kontrole CORS i DataTile nie wczytały kafli.
To nowy dowód ponad poniższą analizę z 2026-10-30; stan silników opisuje
raport. Nie zalicza natywnego Safari/iPhone ani Androida.
QGIS WASM nie był ponownie badany.

Stan źródeł: **2026-10-30**, qgis-js / `@qgis-js/ol` **4.2.3**, OpenLayers **10.11.0**. Zakres decyzji: mapa GitHub Pages w EPSG:2180, historia GPS, 73 modele ciągów i katalog 814 planów. To analiza dokumentacji i kodu, bez benchmarku przeglądarki. Liczby dotyczące całego katalogu i transferu aplikacji wymagają oddzielnego pomiaru.

Aktualizacja decyzji po przeglądzie z użytkownikiem: 2026-10-30.
OpenLayers jest jedynym silnikiem pierwszej wersji mapy 2D w osobnym
repozytorium i na osobnych Pages. Obecne 3D pozostaje bez zmian.
Wersje oraz liczebności w analizie są historycznymi próbkami.
Oddzielne [badanie wydajności](PAGES_MAP_PERFORMANCE.md) opisuje pomiary
prototypu; aktualny kontrakt projektu zawiera [specyfikacja](PAGES_MAP_SPEC.md).
Aktualizacja dokumentu nie stanowi nowego testu kompatybilności upstream.

## Rekomendacja

**Przyjęto OpenLayers jako jedyny renderer nowej mapy. QGIS WASM nie wchodzi do pierwszej wersji, również jako opcjonalny tryb.** Korzyścią qgis-js jest wykorzystanie projektu, symbolizacji i API QGIS; ceną jest dodatkowy runtime, izolacja przeglądarki i niepewność wsparcia mobilnego. Odtwarzanie projektu QGIS nie jest wymaganiem produktu. Nie znaleziono podstaw, aby oczekiwać, że przeniesienie 814 planów do WASM zmniejszy transfer lub automatycznie zapewni strumieniowanie. Jest to wybór zakresu i architektury, nie dowód przewagi wydajnościowej dwóch równoważnych aplikacji.

Dla planów proponuję katalog z zasięgami i adresami wariantów, pobieranie wyłącznie obrazów potrzebnych w bieżącym widoku oraz limit łącznej liczby pikseli w pamięci. Dwa lub kilka poziomów WebP to wariant prosty; kafle albo COG warto porównać dla największych planów. Ostateczny format i progi powinien wyznaczyć pomiar czytelności i transferu reprezentatywnych planów. Widok EPSG:2180 sam w sobie nie wymaga QGIS: OpenLayers obsługuje własne projekcje przez Proj4js oraz reprojekcję rastrów w przeglądarce. [Dokumentacja OpenLayers](https://openlayers.org/doc/tutorials/raster-reprojection.html).

## Co potwierdza kod qgis-js

W źródłach sprawdzonych na datę badania qgis-js jest oznaczony jako public beta. Udostępnia rdzeń QGIS, wczytanie projektu i asynchroniczne renderowanie obrazów. Nie jest aplikacją QGIS Desktop; nie dostarcza PyQGIS ani GUI Qt. **Sieciowe WMS, WFS, WMTS, XYZ, COG i vector tiles są jawnie wymienione jako niewspierane.** [README projektu](https://github.com/qgis/qgis-js/blob/main/README.md#limitations). Linki do gałęzi upstream mogą się zmieniać; przy przyszłej ponownej ocenie trzeba sprawdzić wersję, której dotyczy pytanie.

`@qgis-js/ol` jest mostem między silnikiem QGIS a OpenLayers:

| Źródło | Rzeczywista operacja | Znaczenie dla planów |
| --- | --- | --- |
| `QgisCanvasDataSource` | Wywołuje `renderImage()` dla zasięgu i projekcji widoku, przekazuje `ImageData` do bitmapy. | Renderuje już dostępne dane; nie pobiera rastrów według zasięgu. |
| `QgisXYZDataSource` | Wywołuje lokalne `renderXYZTile()` i wkłada wynik do płótna kafla. | Kafle są wynikiem renderowania QGIS, nie mechanizmem częściowego pobierania źródłowych TIFF-ów. |
| `QgisJobDataSource` | Uruchamia zadanie renderowania, pokazuje podglądy i anuluje poprzednie zadania. | Może poprawić odczucie płynności; nie ogranicza transferu danych wejściowych. |

Źródła implementacji: [Canvas](https://github.com/qgis/qgis-js/blob/main/packages/qgis-js-ol/src/QgisCanvasDataSource.ts), [XYZ](https://github.com/qgis/qgis-js/blob/main/packages/qgis-js-ol/src/QgisXYZDataSource.ts), [Job](https://github.com/qgis/qgis-js/blob/main/packages/qgis-js-ol/src/QgisJobDataSource.ts).

Oficjalny przykład pobiera całe pliki przez `fetch()`/`arrayBuffer()`, zapisuje je do systemu plików runtime przez `fs.writeFile()` i dopiero otwiera projekt. `RemoteProject.uploadProject()` również pobiera wszystkie zadeklarowane pliki. To nie jest automatyczny odczyt HTTP Range. [Przykład OL](https://github.com/qgis/qgis-js/blob/main/docs/examples/qgis-js-example-ol/main.js), [RemoteProject](https://github.com/qgis/qgis-js/blob/main/packages/qgis-js-utils/src/fs/RemoteProject.ts).

Można zaprojektować własne dołączanie plików na żądanie: istnieje `loadLayerDefinition()` dla QLR oraz wybór renderowanych `layerIds`. Dokumentacja nie obiecuje jednak automatycznego pobierania i zwalniania danych rasterowych. „Lazy iteration” w changelogu dotyczy iteratora obiektów wektorowych, a nie transferu plików przez sieć. [Changelog API](https://github.com/qgis/qgis-js/blob/main/CHANGELOG.md#420-6-july-2026).

## COG, transfer i koszt runtime

OpenLayers ma źródło GeoTIFF oparte na geotiff.js i oficjalny przykład COG. geotiff.js wysyła żądania `Range`, obsługuje odpowiedź `206` i domyślnie odrzuca pełny plik, gdy serwer ignoruje zakres. **COG jest zatem opcją po stronie OpenLayers; nie jest obecnie obsługiwaną warstwą sieciową qgis-js.** Warunkiem wyboru COG jest sprawdzenie finalnego hosta, odpowiedzi `206`, CORS przy obcym originie oraz układu kafli i overview w plikach. [OL GeoTIFF](https://openlayers.org/en/latest/apidoc/module-ol_source_GeoTIFF-GeoTIFFSource.html), [przykład COG](https://openlayers.org/en/latest/examples/cog.html), [kod geotiff.js](https://github.com/geotiffjs/geotiff.js/blob/master/src/source/remote.js).

Oficjalna tabela qgis-js 4.2.3 podaje **77,64 MB bez kompresji, 18,8 MB Brotli lub 22,12 MB gzip** dla pakietu runtime. To nie obejmuje planów, danych GPS ani modeli. Tabela opisuje rozmiar artefaktów, nie całkowitą pamięć procesu i nie gwarantowany transfer danego hostingu. [Rozmiary pakietu](https://github.com/qgis/qgis-js/blob/main/packages/qgis-js/README.md#size).

Lokalnie odczytane pliki prototypu mają łącznie 81 400 606 bajtów (`wasm`, `data`, glue JS); ich przygotowane `.gz` mają 22 942 193 bajty. Różnica względem zaokrąglonej tabeli upstream wymaga używania rzeczywistych artefaktów w budżecie aplikacji. Pomiar rozmiaru pliku nie dowodzi, że GitHub Pages wyśle ten wariant z właściwym `Content-Encoding`.

## GitHub Pages, izolacja i podkłady TPN

qgis-js wymaga `SharedArrayBuffer`, wątków WASM i izolacji cross-origin. Oficjalna dokumentacja wskazuje COOP/COEP oraz `coi-serviceworker` jako drogę uruchomienia na GitHub Pages. Service worker musi być z tego samego originu, działa pod HTTPS i przy pierwszej wizycie przeładowuje stronę. To dodatkowa ścieżka startu i utrzymania. [Wymagania qgis-js](https://github.com/qgis/qgis-js/blob/main/docs/compatibility.md), [coi-serviceworker](https://github.com/gzuidhof/coi-serviceworker#usage).

Dla podkładu TPN **bez nagłówka CORS** trzeba rozróżnić przypadki:

- `crossOrigin: 'anonymous'` lub `fetch()` w trybie CORS nadal wymaga zgody serwera. COEP ani service worker nie znosi CORS.
- `COEP: require-corp` blokuje obraz `no-cors` z obcego originu, jeśli nie ma odpowiedniego CORP.
- `COEP: credentialless` dopuszcza pewne obrazy `no-cors` bez CORP, wysyłając je bez credentials; nie daje prawa odczytu ich pikseli. Nie naprawia żądań `cors`.

Źródło zasad: [MDN COEP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Embedder-Policy).

W zwykłym OpenLayers Canvas2D obraz bez CORS może być wyświetlany kosztem „tainted canvas”: odczyt pikseli i eksport takiego płótna są blokowane. Nie należy z tego wyciągać ani ogólnego zakazu reprojekcji, ani gwarancji działania konkretnego podkładu; docelowa ścieżka TPN → EPSG:2180 wymaga testu w przeglądarkach. [Parametr `XYZ.crossOrigin`](https://openlayers.org/en/latest/apidoc/module-ol_source_XYZ-XYZ.html), [zasady canvas](https://developer.mozilla.org/en-US/docs/Web/HTML/How_to/CORS_enabled_image).

Nowy projekt nie wymaga QGIS WASM, więc nie należy przenosić do niego
izolacji COOP/COEP i service workera wyłącznie z powodu starego prototypu.
Wybrana ścieżka TPN musi zostać sprawdzona bez proxy na nowych Pages.
Uzgodniony fallback OSM z komunikatem służy awarii podczas oglądania;
nie zastępuje poprawnej integracji TPN przy odbiorze.

Lokalny proxy Vite nie zostaje usługą proxy po opublikowaniu `dist/`: Pages jest hostingiem statycznym. Udane uruchomienie localhost nie potwierdza zatem działania TPN ani kompresji runtime na Pages. Wielkość opublikowanej witryny ma limit 1 GB; miesięczny transfer ma miękki limit 100 GB. [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [limity](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

## Stan lokalnego prototypu i nierozstrzygnięte kwestie

Odczytano kod w `/Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr/build/qgis-web`; niczego tam nie zmieniono:

- `main.js` pobiera całą paczkę `katalog-qgis.zip`, rozpakowuje ją, kopiuje pliki do runtime i renderuje dane QGIS przez `QgisCanvasDataSource` w EPSG:3857.
- `georeferencer.js` renderuje plany osobno jako `ImageStatic` w OpenLayers. Dobiera wariant według rozmiaru ekranowego, ogranicza aktywne obrazy do 24 warstw i 32 × 1024² pikseli, zwalnia poprzednie warstwy. To ograniczenia aplikacji, nie funkcje WASM. Prototyp odnosi się do 815 planów v0.7.3; nie jest pomiarem aktualnego katalogu 814 planów.
- `vite.config.js` zapewnia COOP/COEP, własne podawanie `.gz` oraz proxy `/tpn-tiles`. Te trzy elementy wymagają osobnego rozwiązania lub weryfikacji dla statycznego wdrożenia.

Ten katalog pozostaje poza nowym projektem, wyłącznie jako lokalny materiał
badawczy. Nowy build ma samodzielnie pobierać wybrane release assets;
nie zakłada istnienia prototypu, lokalnej paczki PR ani instalacji QGIS.

Dokumentacja kompatybilności nadal deklaruje wsparcie/testy desktopowego Chromium ≥95 i Firefox ≥100, brak wsparcia mobile oraz nietestowane Safari. Jednocześnie changelog 4.2.3 z 1 października 2026 zawiera poprawkę GitHub Pages dla Safari iOS/macOS. To **niespójność dokumentacji**, nie dowód, że iPhone nie uruchomi mapy; nie wystarcza też do obietnicy wsparcia mobilnego. [Kompatybilność](https://github.com/qgis/qgis-js/blob/main/docs/compatibility.md#supported-browsers), [changelog 4.2.3](https://github.com/qgis/qgis-js/blob/main/CHANGELOG.md#423-1-october-2026).

Do rozstrzygnięcia przez pomiary pozostają: start z pustym cache na Pages, rzeczywiste `Content-Encoding`, pamięć i stabilność na telefonie, dostęp TPN bez proxy w EPSG:2180, jakość drobnych napisów WebP, koszt największych planów oraz odpowiedzi Range dla ewentualnych COG. Żadnej z tych wartości nie można wyprowadzić wyłącznie z faktu użycia WebAssembly.

Wymagane telefony nowej mapy to Android/Chrome i iPhone/Safari, sprawdzone
na rzeczywistych urządzeniach. COG pozostaje otwartym wyborem formatu
w OpenLayers; brak wsparcia w qgis-js nie jest powodem jego odrzucenia.

## Ponowna weryfikacja TPN i OpenLayers — 2026-10-30

Poniższe uzupełnienie jest analizą konfiguracji, odpowiedzi HTTP i kodu.
Nie zbudowano nowej aplikacji ani nie opublikowano próbki Pages.

[Konfiguracja TPN](https://tpn.obliview.com/Data/conf.json) podaje dla
`rgb_2020`, `rgb_2018`, `NMT`, `nmpt` adresy
`https://tpn.obliview.com/Data/{zbiór}/{z}/{x}/{y}.jpg` i zakres 15–20.
Źródła korzystają ze standardowej siatki XYZ/EPSG:3857: wynika to z
[kodu aplikacji TPN](https://tpn.obliview.com/init.js), używającego domyślnego
widoku OpenLayers we współrzędnych Mercatora; konfiguracja nie zawiera
oddzielnego pola CRS przy każdym zbiorze. To ustalenie struktury źródła,
nie walidacja położenia każdego kafla.

Próbki HEAD z nagłówkiem `Origin: https://example.github.io`, odczytane
2026-10-30 o 20:42:52 UTC:

| Zbiór | Kafel `17/72811/44862.jpg` | Typ | Content-Length |
| --- | --- | --- | ---: |
| [RGB2020](https://tpn.obliview.com/Data/rgb_2020/17/72811/44862.jpg) | 200 | image/jpeg | 24 633 B |
| [RGB2018](https://tpn.obliview.com/Data/rgb_2018/17/72811/44862.jpg) | 200 | image/jpeg | 17 908 B |
| [NMT](https://tpn.obliview.com/Data/NMT/17/72811/44862.jpg) | 200 | image/jpeg | 20 715 B |
| [NMPT](https://tpn.obliview.com/Data/nmpt/17/72811/44862.jpg) | 200 | image/jpeg | 30 451 B |

W tych odpowiedziach nie było `Access-Control-Allow-Origin` ani
`Cross-Origin-Resource-Policy`. Udane HEAD nie dowodzi dekodowania JPEG-a
ani renderowania. Próbki `15/18202/11215` i `20/582488/358898` zwróciły 200
dla czterech warstw. RGB2020 miało też 200 dla `14/9101/5607`, więc zakres
15–20 jest deklaracją konfiguracji, a nie inwentaryzacją całej piramidy.

Próbka `17/72806/44888` zwróciła 404 dla
[NMT](https://tpn.obliview.com/Data/NMT/17/72806/44888.jpg) i
[NMPT](https://tpn.obliview.com/Data/nmpt/17/72806/44888.jpg), ale 200 dla
[RGB2020](https://tpn.obliview.com/Data/rgb_2020/17/72806/44888.jpg).
Nie wolno traktować pojedynczego błędu jako awarii całego TPN.
`SETTINGS.bbox` opisuje ustawienie aplikacji, a
[zakres.geojson](https://tpn.obliview.com/Data/zakres.geojson) granice parku
z metadanymi BDOT; żaden z nich nie potwierdza footprintu każdego zbioru.

W OpenLayers 10.11.0 istotne są dwie różne ścieżki:

- [`ol/source/XYZ`](https://github.com/openlayers/openlayers/blob/v10.11.0/src/ol/source/XYZ.js)
  przez `TileImage` i `reproj/Tile` używa
  [reprojekcji Canvas2D](https://github.com/openlayers/openlayers/blob/v10.11.0/src/ol/reproj.js).
  `getImageData()` dotyczy własnego testowego płótna 6×6; przekształcanie
  obrazów źródłowych używa `drawImage`, transformacji i przycinania.
  Nie znaleziono obowiązkowego odczytu pikseli źródłowych w tej ścieżce.
- [`ol/source/ImageTile`](https://github.com/openlayers/openlayers/blob/v10.11.0/src/ol/source/ImageTile.js)
  dziedziczy po DataTileSource. Domyślne `crossOrigin` to `anonymous`,
  a [reprojekcja DataTile](https://github.com/openlayers/openlayers/blob/v10.11.0/src/ol/reproj/DataTile.js)
  wywołuje [`toArray()`](https://github.com/openlayers/openlayers/blob/v10.11.0/src/ol/DataTile.js)
  z odczytem pikseli. Ta ścieżka wymaga CORS.

Rekomendacja: dla TPN sprawdzić pierwszą ścieżkę z nieustawionym
`crossOrigin`. Nazwa „Canvas2D” sama nie opisuje wystarczająco kontraktu.
Nie przenosić ścieżki automatycznie na WebGL/DataTile ani nie dodawać
odczytu pikseli przy późniejszej zmianie renderera. Weryfikację kodu trzeba
powtórzyć po zmianie wersji OpenLayers.

Obsługa błędów pozostaje oparta na możliwości wczytania obrazu:
[loader](https://github.com/openlayers/openlayers/blob/v10.11.0/src/ol/ImageTile.js)
nie przekazuje do aplikacji kodu HTTP. Specyfikacja proponuje OSM pod TPN,
komunikat o brakujących kaflach i ograniczone ponowienia zamiast
diagnozowania awarii całej usługi na podstawie jednego zdarzenia.

Po późniejszej publikacji sondy z 2026-10-31 potwierdzono cztery podkłady
w EPSG:2180 z docelowego Pages w Chromium i desktopowym WebKit, bez proxy.
W Chromium sprawdzono też skale, luki, krycie, obrót oraz wymuszoną awarię
i ręczny powrót. Szczegóły i brakujące silniki opisuje raport przeglądarki.
Nadal wymagane są natywne Safari, iPhone 14 Pro wskazany przez użytkownika
i rzeczywisty Android, pełniejsze testy szwów i stabilności. Celowy odczyt
pikseli TPN ma być zabroniony; oczekiwany `SecurityError` nie jest awarią
ścieżki wyświetlania.
