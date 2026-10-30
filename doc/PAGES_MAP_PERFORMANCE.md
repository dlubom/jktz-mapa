# Plany jaskiń: pomiary ładowania i ocena QGIS WASM

Badanie: 2026-10-30. Wynik dotyczy prototypów i próbek, nie gotowego serwisu
Pages. Źródło planów: [Georeferencer v0.7.4](https://github.com/dlubom/Georeferencer/releases/tag/v0.7.4).
SHA-256 archiwum: `52a7f5a9238e5f4a2836b61f09cfe403ef101bcc3378fd4a27642f13db62d93b`.

Aktualizacja wniosków projektowych: 2026-10-30, po przeglądzie z użytkownikiem.
Nie wykonano przy tej aktualizacji nowych pomiarów. Wersje i liczebności
poniżej opisują próbki badawcze, nie przyszłe przypięcia workflow.
Nowa mapa 2D ma osobne repozytorium i Pages; obecne 3D pozostaje bez zmian.
Uzgodniony zakres oraz kwestie otwarte opisuje [specyfikacja](PAGES_MAP_SPEC.md).

## Wniosek

**Ciężarem planów jest liczba pikseli po dekodowaniu, a nie sam ZIP.**
Do publicznej mapy wybrano OpenLayers. Propozycją dostarczania planów są
przygotowane podczas buildu obrazy w kilku rozdzielczościach: małe plany
jako podglądy, duże jako kafle. COG pozostaje alternatywą do porównania;
dotychczasowe badanie nie rozstrzyga ostatecznego formatu pełnego katalogu.
WASM nie zastępuje tej optymalizacji. Zaletą qgis-js jest odtwarzanie projektu
i symbolizacji QGIS; w badanym prototypie dokłada około 23 MB samego silnika
do pierwszego wejścia i nie renderuje planów — robi to osobny kod OpenLayers.

## Rzeczywisty katalog planów

Odczytano manifest i strukturę wszystkich 814 GeoTIFF-ów przez GDAL 3.13.3.
Wszystkie mają jeden kanał 1-bitowy, kompresję CCITT Group 4, pasy TIFF
i **brak overview**. To wydajny format archiwalny dla czarno-białych rysunków,
ale nie gotowa piramida do wybiórczego wyświetlania w przeglądarce.

| Właściwość | Wynik |
| --- | ---: |
| ZIP wydania | 21 746 297 B / 21,75 MB |
| Same TIFF-y po wyjęciu z ZIP | 23 457 928 B / 23,46 MB |
| Liczba pikseli | 5 494 610 208 |
| Teoretyczny bufor RGBA całego katalogu | 20,47 GiB |
| Mediana planu, bufor RGBA | 4,76 MiB |
| 95. percentyl, bufor RGBA | 93,36 MiB |
| Plany wymagające ponad 100 MiB pełnego RGBA | 39 |
| Największy: Miętusia, `001197` | 28 660 × 16 266 px |
| TIFF Miętusiej | 1 314 417 B |
| Pełny bufor RGBA Miętusiej | 1778,35 MiB / 1,74 GiB |

RGBA to obliczenie `szerokość × wysokość × 4`, nie pomiar RSS QGIS.
Silnik natywny może czytać części rastra i używać innych reprezentacji;
z kolei przeglądarka może utrzymywać dodatkowe kopie, tekstury i cache.
Nie należy na tej podstawie twierdzić, że QGIS musi zaalokować cały taki bufor.

## Próba w przeglądarce

Chromium 156 na macOS, widok 1200 × 800, limit sześciu równoległych żądań.
CDP: pobieranie **10 Mb/s**, opóźnienie **80 ms**, HTTP cache wyłączony.
Po trzy próby; podajemy mediany. Serwer lokalny HTTP/1.1 z emulacją sieci,
bez dodatkowej emulacji wolnego CPU. To nie pomiar telefonu ani CDN Pages.

GDAL przeliczył pełną transformację planów do rastrów north-up EPSG:2180.
Próbki WebP są bezstratne względem przeskalowanego obrazu; samo zmniejszanie
rozdzielczości jest przetwarzaniem pochodnym z interpolacją bilinear.
Zachowano białe tło rysunku, alfa dotyczy obszaru poza obrazem źródłowym.
Wszystkie warianty wyświetlono z kryciem 75%.

| Miętusia — sposób dostarczenia | Obrazy | Dane obrazów | Bufory RGBA obrazów | Gotowość obrazu |
| --- | ---: | ---: | ---: | ---: |
| Cały podgląd, szerokość 4096 px | 1 | 463,5 KB | 36,83 MiB | 0,618 s |
| Kafle 512 px, widok 1 m/px | 6 | 81,8 KB | 6,00 MiB | 0,249 s |
| Kafle 512 px, widok 0,25 m/px | 6 | 160,6 KB | 6,00 MiB | 0,314 s |

W pierwszym porównaniu kafle zmniejszyły transfer obrazów o **82,4%**,
bufory o **83,7%**, a czas tej próby o **59,7%**. Warianty nie mają tej samej
liczby pikseli: właśnie dobór rozdzielczości i fragmentu do widoku jest
przedmiotem optymalizacji. Pomiar obejmuje pobranie indeksu próbki,
pobranie i dekodowanie obrazów, rysowanie oraz dwie klatki animacji;
nie obejmuje startu pełnej aplikacji ani podkładów. Próbka używa zwykłego
Canvas 2D, a nie kompletnego renderera OpenLayers z interfejsem mapy.

Oględziny próbki 0,25 m/px potwierdziły czytelność nazw i rysunku w tym
fragmencie Miętusiej. Produkcyjny renderer wymaga jeszcze testów szwów,
gutterów kafli, rotacji, DPR i małych napisów dla szerszej grupy planów.
Nie powiększamy podglądów ponad rozdzielczość źródła.

## Gęste skupiska i liczba żądań

Zbadano widoki 1200 × 800 wycentrowane na każdym planie, kwalifikując
przecięcia prostokątów zasięgu. To konserwatywne oszacowanie; dokładny
obrys obróconego planu może wykluczyć część kandydatów.

| Rozdzielczość | Największa liczba kandydatów w badanej próbie | Z nich o dłuższym boku ≥64 px na ekranie |
| --- | ---: | ---: |
| 2 m/px | 223 | 9 |
| 1 m/px | 122 | 10 |
| 0,5 m/px | 64 | 5 |
| 0,25 m/px | 27 | 16 |

122 obrazy przycięte dokładnie do jednego widoku 1 m/px miały zaledwie
**52,2 KB** i **0,50 MiB RGBA**, lecz ich ładowanie trwało **1,983 s**.
To eksperymentalne wycinki na potrzeby pomiaru, nie gotowa metoda serwowania
statycznej strony: wycinki są dolnym oszacowaniem liczby pikseli względem
siatki kafli. Wynik pokazuje koszt wielu żądań przy małym transferze.
HTTP/2 Pages może zachowywać się inaczej niż lokalny HTTP/1.1.

Hipoteza do sprawdzenia: próg globalny 1 m/px uzupełnić progiem rozmiaru
konkretnego planu — początkowo dłuższy bok co najmniej 64 px CSS.
Bok 64 px nie dowodzi czytelności napisów. Badane centra widoków nie
obejmują wszystkich możliwych pozycji mapy ani DPR telefonów.
Drobne plany pozostają reprezentowane przez obiekty/zasięgi i komunikat
„przybliż, aby zobaczyć plan”. To jawne kryterium skali, zamiast arbitralnego
pokazywania pierwszych 24 planów.

Podczas dopracowania projektu 2026-10-30 ponownie odczytano lokalny
`inventory.json`: szerokość zasięgu Miętusiej `001197` wynosi około
1219,67 m. Dla przykładowej szerokości mapy 390 px CSS dopasowanie
całości wymaga co najmniej 3,13 m/px, jeszcze bez marginesów i wpływu
wysokości dostępnego widoku. To obliczenie z wcześniejszych danych,
nie nowy pomiar przeglądarki ani wybór urządzenia referencyjnego.

**Użytkownik uzgodnił:** „Pokaż cały plan” zawsze pokazuje lekki podgląd
całości wybranego planu, niezależnie od progu automatycznego ładowania;
szczegóły pojawiają się po przybliżeniu. Pozostałe plany nadal podlegają
kryteriom automatycznego ładowania. Nie ma jeszcze pomiaru tego zachowania
w gotowej mapie ani zatwierdzonego rozmiaru podglądu.

## Pomiar istniejącego prototypu QGIS WASM

Przetestowano istniejący build z
`/Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr/build/qgis-web`,
bez zmian jego plików. To lokalny materiał badawczy, nie zależność nowego
repozytorium lub jego workflow.
Zawiera qgis-js 4.2.3, dane GPS/JKTZ z lokalnej paczki PR #39 i indeks
815 planów v0.7.3. To inna migawka planów niż katalog v0.7.4 badany wyżej;
przy starcie nie jest pobierany żaden obraz planu. Stan początkowy tego
prototypu nie ma włączonych wszystkich modeli JKTZ.

Ten sam profil 10 Mb/s / 80 ms i trzy przeładowania z wyłączonym HTTP cache:

| Pomiar | Wynik |
| --- | ---: |
| Gotowość QGIS, pierwszy render i indeks planów | 21,818 / 21,718 / 21,682 s |
| Mediana | **21,718 s** |
| Runtime: WASM + dane + JS, pliki gzip | **22 942 193 B** |
| Te same pliki po dekompresji | **81 400 606 B** |
| Unikalne zasoby lokalne, skompresowane treści | około **24,54 MB** |
| Obrazy planów pobrane przy starcie | **0** |

Suma wszystkich wpisów Resource Timing wynosi 25,23 MB, lecz powiela wpisy
JS workerów. Dlatego nie traktujemy jej jako precyzyjnego pomiaru transferu
po kablu. CDP zakończonych żądań strony wykazało 24,55 MB z nagłówkami,
ale nie dostarczyło zakończenia wszystkich żądań workerów. Uczciwy skrót
to „około 25 MB”, a rozmiar samych plików runtime jest jednoznaczny.

Pomiar JS heap pokazywał około 78 MB, ale **nie jest to całkowita pamięć
QGIS/WASM/GPU**. `measureUserAgentSpecificMemory()` nie zakończyło pomiaru
w 12 s; nie podajemy fikcyjnej wartości RSS. Katalog i runtime trafiają do
pamięci przed otwarciem projektu, podczas gdy plany obsługuje OpenLayers.

To pomiar działającego prototypu QGIS, nie porównanie dwóch gotowych aplikacji
o identycznych funkcjach. Nowa mapa OpenLayers nie ma jeszcze zmierzonego
czasu gotowości; jej cel 3 s pozostaje celem do weryfikacji.

## QGIS, COG i Pages

Dokumentacja qgis-js jawnie wymienia sieciowe COG/XYZ/WMS jako niewspierane.
WASM renderuje dane dostępne w swoim systemie plików; jego adapter OL
nie dodaje automatycznego pobierania fragmentów TIFF. Potrzebuje też
izolacji cross-origin i osobnego rozwiązania dla Pages. Szczegóły oraz
źródła: [analiza QGIS WASM](QGIS_WASM_RESEARCH.md).

COG może być rozważany osobno przez OpenLayers/geotiff.js; nie jest argumentem
za QGIS WASM. Test `Range: bytes=0-15` istniejącego `KATASTER.3d` na domenie
Pages zwrócił HTTP 206 i ACAO `*`, ale z `Content-Encoding: gzip`.
Nie dowodzi to poprawnego odczytu zakresów przyszłego pliku COG: wymaga
sprawdzenia rzeczywistego TIFF-a, MIME, kompresji transportowej i offsetów.
Zwykłe kafle WebP/PNG nie wymagają obsługi HTTP Range.

Dla publicznej mapy po przeglądzie obowiązuje następujące rozróżnienie:

1. Uzgodniono OpenLayers jako jedyny silnik nowej mapy i rzeczywisty widok
   EPSG:2180. Proj4js jest proponowanym uzupełnieniem projekcji.
2. Podglądy do 512 px i kafle 256/512 px są propozycją. Aktualna rekomendacja
   to najpierw sprawdzić ich jakość, koszt oraz rozmiar pełnego katalogu,
   nie tylko trzy próbki. COG pozostaje alternatywą, gdy ten wariant
   nie spełnia wymagań lub wymierna korzyść uzasadnia porównanie; nie ma
   wymagania zbudowania dwóch kompletnych rendererów. Wybór COG nadal
   wymaga sprawdzenia prawdziwego TIFF-a na docelowym Pages.
3. 64 MiB aktywnych zdekodowanych obrazów i sześć równoległych pobrań
   to budżety próbne. Nie określają całkowitej pamięci procesu/GPU.
4. QGIS WASM nie wchodzi do pierwszej wersji, również jako osobny tryb.
   Wybór ten wynika z zakresu produktu i kosztu runtime, a nie z pomiaru
   dwóch równoważnych gotowych aplikacji.
5. Odbiór obejmuje rzeczywiste Android/Chrome i iPhone/Safari oraz TPN
   w EPSG:2180 bez proxy. Awaria TPN podczas używania ma uruchamiać OSM
   z komunikatem; fallback nie zalicza testu poprawnej integracji TPN.

## Dowody i ograniczenia

Skrypty, JSON-y wynikowe i zrzut próbki pozostają w ignorowanym katalogu
repozytorium JKTZ, poza nowym projektem:
`/Users/dariuszlubomski/proj/Jaskiniowy-Kataster-Tatr-Zachodnich/.verification/2026-10-30-map-performance/`:
`measure_plans.py`,
`build_dense_view.py`, `inventory.json`, `raster-variants.json`,
`dense-view.json`, `raster-browser.json`, `qgis-perf-1.json`,
`qgis-perf-23.json`, `index.html`, `mietusia-025.png`.
Materiały te nie zostały przeniesione wraz z dokumentami i nie są dostępne
w świeżym klonie. Przed usunięciem starego checkoutu trzeba osobno zachować
potrzebne dowody. Nie są wejściami produkcyjnego workflow.
Źródłowych TIFF-ów, prototypu QGIS i README projektu nie zmieniono.

Przed odbiorem pozostają: właściwa mapa z wszystkimi funkcjami, testy
na docelowym Pages, telefon, pełna pamięć procesu, zimny start nowego
profilu przeglądarki, cała piramida i jej rozmiar, prawidłowa georeferencja
oraz bezpośrednie podkłady TPN w EPSG:2180 bez lokalnego proxy.

Cele 1 MB aplikacji i indeksów, 3 s gotowości oraz p95 klatki 33 ms nie są
wynikami tego badania. Następny projekt pomiaru musi wskazać urządzenia,
warstwy wymagane w momencie „gotowości”, profil sieci i sposób pomiaru
pamięci. Brak pomiaru lub urządzenia należy raportować jako brak dowodu.

Ustalenie organizacyjne z dopracowania projektu 2026-10-30: użytkownik
wykona odbiór na własnym iPhonie 14 Pro. To deklaracja przyszłego testu,
nie wynik ani dowód zgodności. Android/Chrome nadal wymaga wskazania
rzeczywistego urządzenia. Scenariusze i rozróżnienie gotowości interfejsu,
gotowości widoku oraz pełnej pamięci opisuje specyfikacja.
