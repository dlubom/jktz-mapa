# Mapa JKTZ 2D — specyfikacja robocza po przeglądzie

Aktualizacja: 2026-10-31. Etap: dopracowanie projektu oraz lokalne
i osobno zatwierdzone próby GitHub, przed pełną implementacją.
Uzgodnione wymagania opisano oddzielnie od propozycji technicznych i kwestii
wymagających dowodów. Dokument nie zatwierdza całej implementacji.

Nowsze polecenie użytkownika dopuściło odrzucalne próby lokalne. Wyniki:
[TPN i rastry w przeglądarce](PAGES_BROWSER_PROBE.md),
[kontrakty źródeł i pełny katalog rastrów](PAGES_INPUTS_RASTERS_PROBE.md),
[publikacja i odzyskiwanie](PAGES_PUBLICATION_RESEARCH.md).
Po osobnej zgodzie użytkownika opublikowano małą sondę TPN na Pages.
Potwierdzono sumy publicznych plików i renderowanie w Chromium/WebKit;
szczegółowy stan przeglądarek i urządzeń jest w raporcie. Nie jest to pełna
aplikacja ani dowód jej gotowości. Tymczasowa publikacja z `gh-pages`
nie wdraża docelowego workflow danych i rollbacku.

Lokalny model publikacji, retencji, rollbacku i odzysku sprawdzono następnie
kontrolowanymi awariami. [Wyniki i przygotowana próba GitHub](PAGES_PUBLICATION_PROBE.md)
oddzielają dowód lokalny od [osobno zatwierdzonej próby Actions/Pages](PAGES_PUBLICATION_GITHUB_TRIAL.md).
Potwierdzono kolejkę dwóch oczekujących runów, blokadę przez `pending`
oraz odzysk B po anulowaniu runu **po ukończonym kroku deployu**.
Powtórny odzysk nie uruchomił deployu ani nie zmienił bajtów i SHA ewidencji.
Rollback A zakończył się sukcesem, a ponowiony stary B pominięto bez deployu
i zmiany ewidencji. Próbę zakończono wdrożeniem paczki oryginału,
przywróceniem Pages do `legacy`, źródła `gh-pages:/` i pierwotnej reguły
środowiska; workflow próby wyłączono. Publiczne pliki są zgodne, marker
próby zwraca 404. Nie jest to gwarancja odzysku przerwania wewnątrz deployu.
Pełna aplikacja i produkcyjny workflow nadal wymagają osobnej zgody.

## Uzgodniony zakres i miejsce projektu

Polska, statyczna mapa pozycji obiektów, dostępnej historii pomiarów,
ciągów JKTZ i planów Georeferencera. Użytkownik może wyszukać obiekt,
porównać źródła oraz sprawdzić pochodzenie i niepewność danych.
Mapa korzysta z migawki przygotowanej przy wdrożeniu.

- Mapa 2D ma **osobne repozytorium GitHub**, a docelowo własne Pages
  i ręczny workflow. Roboczy katalog: `jktz-mapa`;
  [repozytorium](https://github.com/dlubom/jktz-mapa) utworzono 2026-10-30
  na osobne polecenie użytkownika, aby zapisać dokumentację w Git.
  Po późniejszej osobnej zgodzie z 2026-10-31 Pages pokazuje wyłącznie
  sondę TPN; nie rozpoczęto pełnej implementacji aplikacji.
- Obecna przeglądarka CaveView 3D w JKTZ, jej adres, wygląd i publikacja
  pozostają bez zmian. Nie przenosimy jej pod `3d/`, nie zastępujemy strony
  głównej JKTZ i nie tworzymy wspólnej paczki. Serwisy mogą używać różnych
  migawek JKTZ zgodnie ze swoimi wdrożeniami.
- Jedynym silnikiem nowej mapy jest **OpenLayers**. QGIS WASM pozostaje
  materiałem porównawczym poza zakresem pierwszej wersji.
- Odbiór obejmuje komputer oraz rzeczywiste Android/Chrome i iPhone/Safari.
- Użytkownik zadeklarował test na własnym **iPhonie 14 Pro** (2026-10-30).
  Wersję iOS/Safari zapisujemy przy teście. Model i dostępność urządzenia
  Android/Chrome nie zostały jeszcze wskazane; jego odbiór pozostaje otwarty.
- README pozostaje bez nowych informacji i linków do Pages.

Nowy projekt wymaga własnych, proporcjonalnych narzędzi i bramek jakości.
Nie dziedziczy automatycznie struktury `src/jktz/`, CLI `jktz-*` ani procesu
walidacji pomiarów z repozytorium danych JKTZ.

## Najważniejszy kontrakt: jedno kliknięcie

Po jednorazowym skonfigurowaniu Pages w nowym repozytorium kliknięcie
**Run workflow** uruchamia cały proces bez obowiązkowych parametrów wersji:

Każdy nowy poprawny przebieg publikuje aktualną migawkę po sprawdzeniach,
o ile nie został zastąpiony nowszą zakończoną operacją deployu/rollbacku.
Rekomendacja techniczna: brak zmiany trzech źródeł nie pomija zmian
aplikacji lub profilu przetwarzania; tożsamość paczki uwzględnia także te
wejścia. Ponowna publikacja dokładnie tej samej bieżącej paczki nie
oznacza jej zastąpienia i nie rozpoczyna terminu usunięcia. Wskazanie
GitHub Latest jest wiążące także wtedy, gdy tag wygląda na starszy;
nie wprowadzamy własnego porządku SemVer.

**Doprecyzowanie użytkownika z 2026-10-30:** każde nowe kliknięcie
„Run workflow” ponownie sprawdza Latest we wszystkich trzech repozytoriach.
Jeśli od poprzedniego wdrożenia pojawiło się nowsze wydanie choćby jednego
źródła, nowy przebieg ma je uwzględnić i automatycznie wdrożyć nową migawkę
po pomyślnej walidacji i buildzie. Nie trzeba czekać na nowe wydania
pozostałych źródeł. Przypięcie „raz na początku” obowiązuje tylko w obrębie
danego przebiegu i jego Re-run, nie między kolejnymi kliknięciami.

Przebieg nowego uruchomienia:

1. Odczyt GitHub **Latest** dla każdego źródła:
   - `dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich`,
   - `dlubom/gps-kataster-obiektow-tatr`,
   - `dlubom/Georeferencer`.
2. Kontrola `draft=false` i `prerelease=false`, zapis wydań, rzeczywistych
   commitów tagów i konkretnych zasobów raz na początku. „Latest” oznacza
   wskazanie GitHub, nie własne sortowanie SemVer lub dat.
3. Pobranie zasobów, kontrola integralności, bezpieczne rozpakowanie
   i techniczna walidacja obsługiwanych formatów.
4. Przygotowanie indeksów, warstw, historii, wariantów rastrów i źródeł,
   wykonanie testów oraz build kompletnej statycznej strony.
5. Automatyczne opublikowanie gotowej paczki na Pages nowego repozytorium.

Normalny przebieg nie wymaga lokalnych paczek, ręcznego eksportu QGIS,
pobierania plików przez użytkownika, wpisywania wersji, dodatkowego
zatwierdzenia wdrożenia ani drugiego ręcznego etapu publikacji.
Workflow działa w repozytorium nowych Pages; trzy repozytoria źródłowe
są tylko do odczytu. Lokalny checkout JKTZ i prototyp QGIS nie są
zależnościami buildu ani działającej strony.

Dalsze kroki używają zapisanych wyborów, nawet jeśli pojawi się nowsze
wydanie. Trzy odczyty Latest są sekwencją przypięć źródeł, nie transakcją
zapewniającą wspólny moment wydania trzech repozytoriów.
Metadane uzupełniające, np. szablon otworów JKTZ, trzeba pobrać
automatycznie z dokładnego commitu wybranego wydania; również należą
do manifestu wejść. Brak wymaganego zasobu albo nieobsługiwany format
zatrzymuje przebieg. Nie wybieramy wtedy starszego wydania.
Nowy format może wymagać aktualizacji importera — automatyczne dostosowanie
do dowolnych przyszłych zmian nie jest obietnicą.

Strona nie odświeża katalogów z API Latest w przeglądarce. Nową migawkę
wprowadza kolejne ręczne uruchomienie. TPN i OSM pozostają zewnętrznymi
podkładami pobieranymi podczas oglądania mapy.

## Granice walidacji i zachowanie danych

Walidacja jest **techniczna**: wymagane zasoby i składowe, integralność
archiwów, obsługiwane wersje schematów, wymagane pola, deklaracje CRS
i możliwość odczytu oraz przetworzenia. Kontrakty importerów poniżej opisano
na podstawie rzeczywistych paczek. Liczebności z raportów są próbkami,
a nie stałymi walidatora.

Nie wykonujemy ponownego audytu pomiarów, wyboru Best, orientacji planów
ani kompletności katalogowych powiązań. Ograniczenia materiału źródłowego
nie blokują publikacji. Udostępniamy istniejące metadane i niepewności,
bez dopisywania brakujących informacji.

Rozróżnienie techniczne: poprawnie brakująca relacja katalogowa pozostaje
brakiem. Uszkodzona struktura (np. wskazanie Best na nieistniejący pomiar
danego obiektu albo zduplikowany klucz) zatrzymuje importer. Nie służy to
ocenie, czy wybór Best był merytorycznie właściwy.

- Widok, podziałka i odczyt współrzędnych: **EPSG:2180**, metry.
  Etykiety: `X — północ`, `Y — wschód`; wewnętrzny porządek biblioteki
  mapowej to easting/northing. Odczyt przeliczonych współrzędnych nad
  widokiem EPSG:3857 nie spełnia wymagania.
- Reprojekcja tworzy dane pochodne. Zachowujemy dostęp do oryginalnych
  współrzędnych, CRS, wysokości, transformacji rastrów i metadanych.
  Widok 2D jest rzutem ciągów; nie usuwa źródłowego Z.
- Ciągi pochodzą z eksportów wybranego wydania JKTZ. Nie kompilujemy ich
  ponownie z aktualnym GPS. Planów nie przesuwamy do nowego Best.
  Historyczne wersje GPS w źródłach mogą różnić się od obecnego Latest.
- Relacje wykorzystują jawne ID i dostępne mapowania źródłowe, także
  dla systemów o wielu jaskiniach i otworach. Brak mapowania nie upoważnia
  do zgadywania po podobieństwie nazwy albo geometrii.
- Georeferencja uwzględnia pełną transformację, obrót i konwencję
  środka/narożnika piksela. Prostokąt zasięgu nie zastępuje transformacji.
  Niezweryfikowana orientacja zachowuje oznaczenie źródłowe.

## Kontrakty wejść — zweryfikowany profil z 2026-10-30

Kontrola 2026-10-31 ponownie potwierdziła te trzy Latest/commity, sumy
czterech assets, 2442 składników manifestu Geo i 814 metadanych `meta.yaml`.
Próba odrzuciła pięć kontrolowanych wad danych. To sonda kontraktów,
nie komplet produkcyjnych importerów; szczegóły i ograniczenia zawiera
[raport wejść](PAGES_INPUTS_RASTERS_PROBE.md).

Poniższe wersje są próbką do zaprojektowania importerów, **nie stałym
przypięciem przyszłego workflow**. Odpowiedzi GitHub Latest oraz lokalne
archiwa sprawdzono ponownie; sumy archiwów odpowiadały `assets[].digest`.
Wszystkie trzy wydania były niedraftowe, stabilne i `immutable=false`.
Tagi są annotated: przypięcie wymaga rozwiązania obiektu tagu do commitu.
`target_commitish`, wskazujące gałąź, nie jest takim przypięciem.

| Źródło | Latest / release ID | Rozwiązany commit |
| --- | --- | --- |
| [JKTZ](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/releases/tag/v1.4.12) | `v1.4.12` / `426443343` | `3f865414d1dacaa15cd5477e567b0f852c43b32d` |
| [GPS](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/tag/v1.3.2) | `v1.3.2` / `423386015` | `13d734213328e5491c1a5c3171e2cb0fdcef705c` |
| [Georeferencer](https://github.com/dlubom/Georeferencer/releases/tag/v0.7.4) | `v0.7.4` / `429377515` | `a47c390955db88d7bdbb4eada4a9315884e9ccbe` |

| Wymagany asset próbki | Asset ID | Rozmiar |
| --- | --- | ---: |
| `JKTZ-v1.4.12.zip` | `684414283` | 22 002 141 B |
| GPS `katalog.sqlite.zip` | `674981453` | 535 497 B |
| GPS `metadata.json` | `674981456` | 270 B |
| `geotiff-tatry-v0.7.4.zip` | `693073187` | 21 746 297 B |

Oczekiwane SHA-256 próbki, w kolejności tabeli:

```text
4e2b30ead79ee520c3a9fca84786e3112801fe8d7723d527bc07d81698cbbc91
b93b6ecfbf51a306d603abdea25f91d017313fa9d6d57288a64291f09c70e4b6
e51abd42c25791ada468e9736078a2ad669b055ef06277fffd955f3722cf9821
52a7f5a9238e5f4a2836b61f09cfe403ef101bcc3378fd4a27642f13db62d93b
```

Importer zapisuje osobno oczekiwany digest z API/manifestu, rzeczywisty
SHA-256 pobranych bajtów oraz wynik porównania. Dla release assets obecny
kontrakt wymaga `sha256:` z API; jego brak zatrzymuje import z komunikatem
o nieobsługiwanym kontrakcie integralności. Nie zamieniamy weryfikacji
na samo wyliczenie własnej sumy. Metadane z repozytoriów mają przypięty
commit i ścieżkę oraz hash pobranej treści; Git blob SHA nie jest SHA-256.

### JKTZ

- Asset `JKTZ-{tag}.zip`; modele w `exports/caves/{model_id}` z kompletem
  `.shp`, `.shx`, `.dbf`, `.prj`. W próbce nie ma `.cpg`; nie jest wymagany.
  Profil próbki: PolyLineZ (typ 13), EPSG:32634, 73 modele. Zachować Z.
- Importować modele osobno; `exports/JKTZ-{tag}-all.*` jest alternatywnym
  eksportem zbiorczym, a nie dodatkową kopią ciągów do nałożenia.
- DBF zawiera `Layer`, `PaperSpace`, `SubClasses`, `Linetype`, `EntHandle`,
  `Text`, ale nie `object_id`. ID modelu odpowiada prefiksowi stacji przed
  pierwszym `:` zgodnie z
  [eksporterem wydania](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/blob/3f865414d1dacaa15cd5477e567b0f852c43b32d/src/jktz/exports/pipeline.py).
- Jawne relacje odczytać z `gps_fix(station, object_id)` w
  [Poligony/OTWORY.SRV.j2](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/blob/3f865414d1dacaa15cd5477e567b0f852c43b32d/Poligony/OTWORY.SRV.j2)
  z przypiętego commitu. Szablon jest
  [wykluczony z ZIP-a](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/blob/3f865414d1dacaa15cd5477e567b0f852c43b32d/src/jktz/packaging.py).
  Odczytać go jako dane, bez wykonania/renderowania. Zakomentowane wartości
  kontrolne nie są aktywnymi powiązaniami. Brak relacji pozostaje brakiem;
  szablon nie gwarantuje kompletności otworów systemu.
- Nie ma wersjonowanego manifestu paczki; importer ma własny jawny profil
  obsługiwanego układu, składników SHP i CRS. Zmiana wymaganego układu
  zatrzymuje import; nie zmienia się w audyt pomiarów.

### GPS

- Podstawą jest `katalog.sqlite.zip` z `katalog.sqlite` oraz `metadata.json`.
  Best CSV/GeoJSON i SHP nie zastępują bazy historii; SHP skraca uwagi.
- Obsługiwane wersje: `metadata_schema_version=1`, `data_schema_version=1`
  oraz tekstowe `schema_version="1"` w tabeli SQLite `metadata`.
  `counts` służy raportowi, nie zamrożeniu liczby rekordów.
- Potrzebne tabele: `objects`, `caves`, `measurements`, `best_measurements`,
  `object_external_refs`, `cave_external_refs`, `relations`, `attachments`,
  `metadata`. `validation_flags` pozostają informacją źródła.
- Klucz pomiaru to **`(object_id, id)`**; `best_measurements.measurement_id`
  wskazuje pomiar w obrębie obiektu. Zachować pola geometrii, Z/datum,
  dokładności, źródeł, dat, metody, urządzenia, statusów, notatek i tagów.
  Puste pola opcjonalne nie zatrzymują importu ani nie otrzymują domyślnych
  danych merytorycznych.
- `x_1992` oznacza północ, `y_1992` wschód. `geom_1992` to tekst
  `POINT(y_1992 x_1992)` bez SRID; CRS wynika z kontraktu eksportera.
  WGS84 ma porządek `POINT(lon lat)`.
- `objects.cave_id`, `caves.object_ids_json`, `system_name` i tabele
  referencji rozróżniają obiekt, jaskinię i system. Nie utożsamiać ID
  otworu z identyfikatorem jaskini PIG. Brak osobnej tabeli aliasów:
  wyszukiwarka nie obiecuje kompletnego zbioru aliasów wywnioskowanych
  z notatek; zachowuje dostępne nazwy, identyfikatory i tekst źródłowy.
- Rzeczywisty schemat `attachments` zawiera m.in. `kind`, `path`, `caption`,
  a nie starsze `type/description` z opisu. Kontrakt opiera się na
  [DDL wydania](https://github.com/dlubom/gps-kataster-obiektow-tatr/blob/13d734213328e5491c1a5c3171e2cb0fdcef705c/src/gps_kataster_obiektow_tatr/build_db.py)
  i potwierdzonej strukturze SQLite. Ścieżka załącznika nie gwarantuje,
  że jego zawartość jest dostępna w release; nie tworzyć niedziałających
  linków z samych lokalnych ścieżek.

### Georeferencer

- Asset `geotiff-tatry-{tag}.zip`; obsługiwany manifest:
  `schema_version=1`, `status="complete"`, `content_version="t10-content-v1"`,
  `release.version="t11-v2"`, model geometrii `t06-local-similarity-v1`.
- `release.files[]` wiąże `plan_id`, `output`, `archive_path`, `sha256`.
  Używać tego mapowania, nie odgadywać ID z nazwy TIFF-a. Weryfikować sumy
  składowych. Próbka zawiera 814 planów; nie jest to liczba wymagana.
- Zachować `dir_id`, `measurement`, `inputs`, `outputs`, `acceptance`
  (CRS, rozmiar i geotransformację), `parameters`, `orientation` i
  `coordinate_source`. TIFF-y próbki mają EPSG:2180, jeden kanał 1-bitowy
  i CCITT Group 4. Pełna transformacja może zawierać obrót; TFW opisuje
  środki pikseli, a GDAL narożniki.
- ZIP zawiera TIFF-y, `manifest.json` i `metadane/{plan_id}/image.tfw`,
  `computed.json`. **Nie zawiera `meta.yaml`, `source.json`,
  `image-identity.json`.** `data/caves/{dir_id}/meta.yaml` pobierać z commitu
  wydania i porównywać z `plans[].inputs["meta.yaml"]`; w próbce potwierdzono
  zgodność 814/814. Dostępne uzupełnienia proweniencji pobierać z tego
  samego commitu, jeśli istnieją; brak opcjonalnego opisu pozostaje brakiem.
- Wariant `001459-pza-2024` wskazuje `cave.source_cave_id="001459"`.
  `dir_id` ani ID obrazu nie muszą należeć do przestrzeni PIG.
  Absolutne `source_directory` z manifestu nie jest zależnością workflow.
- Nie przypisywać planom automatycznie licencji GPS/JKTZ: zachować
  deklaracje dostępne w metadanych i jawne braki. Źródła kontraktu:
  [układ wydania](https://github.com/dlubom/Georeferencer/blob/a47c390955db88d7bdbb4eada4a9315884e9ccbe/pipeline/release_layout.py),
  [manifest i transformacje](https://github.com/dlubom/Georeferencer/blob/a47c390955db88d7bdbb4eada4a9315884e9ccbe/docs/GENERATION_OUTPUT.md).

## Interfejs i warstwy

Interfejs jest polski. Propozycja układu: mapa na całe okno, panel boczny
z wyszukiwarką i zakładkami „Warstwy”, „Obiekt”, „Źródła”; na telefonie
panel dolny. Układ wymaga dopracowania. Wymagane są czytelne symbole,
rozróżnienie pozycji katalogowych/GPS, ciągów i planów, obsługa klawiatury,
widoczny fokus oraz komunikaty ładowania i błędów.

| Warstwa | Wymagany stan początkowy |
| --- | --- |
| Best — wybrane pozycje obiektów | Włączona, z nazwami |
| Pozostałe pomiary GPS/katalogowe | Wyłączona; bez Best i odrzuconych |
| Pomiary odrzucone | Wyłączona |
| Linie różnic względem Best | Wyłączona; różnica pozioma w metrach |
| Ciągi JKTZ | Włączone; przełączniki poszczególnych modeli |
| Plany Georeferencera | Włączone; krycie 75%, ładowanie według skali i widoku |

**Uzgodnienie z 2026-10-30:** pokazujemy wszystkie nazwy punktów Best
w bieżącym widoku, również gdy etykiety się nakładają. Nie stosujemy
automatycznego ukrywania kolidujących nazw ani grupowania usuwającego
poszczególne punkty. Możliwe nakładanie napisów jest świadomie przyjętą
konsekwencją; czytelność sprawdzamy przy różnych skalach, zachowując tę
decyzję. Wybór obiektu może wyróżnić jego nazwę, ale nie ukrywa pozostałych.

Wyszukiwanie obejmuje dostępne nazwy, aliasy i identyfikatory, tolerując brak
polskich znaków. Szczegóły pokazują wszystkie pomiary wybranej migawki GPS,
także odrzucone, oraz dostępne daty, autorstwo, metody, źródła, statusy,
dokładności i uzasadnienia Best. „Pełna historia pomiarów” oznacza te
rekordy, nie rekonstrukcję edycji katalogu lub dawnych wyborów Best,
których eksport nie zawiera. Nieznane dane pozostają nieznane;
techniczny autor importu nie jest automatycznie autorem pomiaru.

Best jest wyborem katalogu, nie deklaracją GNSS lub znanej dokładności.
Ukrycie warstwy nie usuwa jej pomiarów ze szczegółów obiektu.
Panel udostępnia dostępne relacje do otworów, modeli i wariantów planów.
Można wybierać plany, nakładać je, zmieniać kolejność i osobno regulować
przezroczystość. Źródła mają właściwe linki, autorstwo, licencje i oznaczenia
niepewności. Rozrzut punktów nie jest miarą dokładności.

## Podkłady

Domyślnie **TPN RGB 2020**, z OSM przy oddaleniu i poza pokryciem.
Alternatywy: TPN RGB 2018, obraz NMT i obraz NMPT. Każdy wybierany podkład
ma regulację krycia i atrybucję; OSM można wybrać samodzielnie.
NMT/NMPT są wyłącznie obrazami i nie służą do odczytu wysokości.

Źródła TPN: `Data/rgb_2020`, `Data/rgb_2018`, `Data/NMT`, `Data/nmpt`
na `https://tpn.obliview.com/`, schemat `{z}/{x}/{y}.jpg`.
Sprawdzona konfiguracja TPN deklaruje poziomy źródłowe 15–20; siatka
wynika z użycia XYZ w EPSG:3857. To poziomy źródła, nie skala widoku
EPSG:2180. Konfiguracja nie stanowi dowodu kompletnego pokrycia.
OSM jest używany zgodnie z polityką dostawcy, bez masowego lub
wyprzedzającego pobierania obszarów.

Niedostępność kafli TPN powoduje pokazanie **OSM i komunikatu**,
z zachowaniem warstw jaskiń. Rekomendacja techniczna: OSM pozostaje pod
TPN, więc brak pojedynczego kafla odsłania podkład lokalnie i nie przełącza
całej mapy. Zbiorczy komunikat mówi o niewczytanej części podkładu, nie
orzeka o awarii serwera. `tileloaderror` nie rozróżnia HTTP 404, problemu
sieci i blokady przeglądarki; różne podkłady mają potwierdzone różnice
dostępności kafli. Nie ustalamy pokrycia na podstawie granicy parku.

Ponowienia są ograniczone, bez nieskończonej pętli; po ich wyczerpaniu
pozostają OSM i „Spróbuj ponownie” dla aktualnego widoku. Udane kafle TPN
mogą pojawić się ponownie bez zmiany wybranego podkładu, skali i warstw.
Parametry ponowień i wygaszania komunikatu wymagają testów pojedynczych
luk, awarii całej usługi i powrotu łączności. Nie potrzeba osobnego monitora
usługi ani odpytywania kafli spoza widoku tylko w celu ustalania przyczyny.

Dotychczasowe HTTP 200 bez CORS nie potwierdza renderowania. Wymagany
jest test TPN → EPSG:2180 bezpośrednio na nowych Pages, we wszystkich
docelowych przeglądarkach, bez proxy Vite i własnego serwera.
Analiza OpenLayers **10.11.0** wskazuje konkretną ścieżkę do testu:
`ol/source/XYZ` → `TileImage` → `reproj/Tile` → Canvas2D, bez ustawiania
`crossOrigin: 'anonymous'`. Nie znaleziono w niej wymaganego odczytu pikseli
obrazów TPN. `ol/source/ImageTile` korzysta natomiast z DataTile i odczytu
pikseli podczas reprojekcji; nie jest zamiennikiem dla źródła bez CORS.
To analiza przypiętej wersji kodu, nie wynik testu przeglądarki. Odczyt
pikseli i eksport płótna z TPN nie należą do tej ścieżki produktu.
Fallback OSM nie zastępuje działającej integracji TPN przy odbiorze.
Dokładne próbki, źródła i ograniczenia opisano w
[analizie podkładów](QGIS_WASM_RESEARCH.md).

**Nowy dowód 2026-10-31:** lokalny statyczny build wyrenderował wszystkie
cztery podkłady przez powyższe `XYZ` w Chromium; kontrole z CORS/DataTile
zawiodły zgodnie z oczekiwaniem. Sprawdzono też DPR 3, luki, wymuszoną
awarię, ręczny powrót, krycie i skale źródłowe 15/20. To uzupełnia analizę
kodu, ale nie zastępuje testu hostingu ani rzeczywistych telefonów.
[Warunki i wyniki](PAGES_BROWSER_PROBE.md).

## Architektura i dostarczanie danych — propozycje techniczne

Przyjęto OpenLayers. Proponowane uzupełnienie: TypeScript, Vite i proj4js,
bez frameworka UI i serwera aplikacji; Python 3.12 oraz GDAL/PROJ do danych
w Actions. Dobór narzędzi, organizacja nowego repo i bramki jakości wymagają
dopracowania. Zależności wymagają powtarzalnych wersji, lockfile'ów
i odpowiednich przypięć obrazów oraz narzędzi.

Na starcie: aplikacja, mały indeks wyszukiwania i zasięgów oraz dane
aktualnego widoku. Historię można pobierać po otwarciu szczegółów.
Podział wektorów zachowuje ID modeli i ich przełączniki.

Plany są pobierane dopiero przy odpowiednim przybliżeniu i tylko dla
aktualnego widoku. Proponuje się podglądy małych planów i kafle dużych.
**COG w OpenLayers pozostaje alternatywą do oceny** na rzeczywistych
plikach z Pages. Test HTTP Range na `.3d` nie rozstrzyga działania COG.
Zachowujemy białe tło skanu; alfa obejmuje obszar poza obrazem źródłowym.
Nie zwiększamy rozdzielczości ponad źródło i nie dekodujemy całych wielkich
TIFF-ów tylko dla wyświetlenia fragmentu. Trzeba sprawdzić drobne napisy,
obrót, DPR, szwy i rozmiar pełnego przygotowanego katalogu.

Rekomendacja techniczna kolejności prac: najpierw zweryfikować wariant
podglądów i kafli, bo odpowiada dotychczasowym próbkom i nie wymaga HTTP
Range. Pełny katalog musi przejść kontrolę rozmiaru, a reprezentatywne
plany kontrolę jakości i kosztu w przeglądarce. Jeśli ten wariant spełni
kryteria, nie trzeba budować drugiego kompletnego renderera dla samego
porównania. COG pozostaje drogą do sprawdzenia, gdy format, wielkość
publikacji lub liczba żądań uzasadnią dodatkową złożoność. Wtedy obowiązuje
próba rzeczywistego COG na Pages, nie ekstrapolacja z `.3d`.
To rekomendacja autora projektu, nie potwierdzony wynik pełnego benchmarku.

**Wynik 2026-10-31 i rekomendacja do następnego etapu:** zmierzona piramida
WebP lossless 512 px całego katalogu wraz z podglądami zajmuje
275 282 006 B (262,53 MiB), 35 845 plików. Dlatego pozostajemy przy
podglądach i kaflach 512; obecne dane nie uzasadniają dokładania COG.
To subtotal rastrów bez gutterów, aplikacji, wektorów i historii,
nie pomiar gotowej strony. Oględziny pięciu planów w OpenLayers DPR 1/3
potwierdziły podglądy i szczegóły; pełna pamięć telefonu, długie używanie,
gęste nakładanie i granice kafli pozostają do testu. [Szczegóły rastrów](PAGES_INPUTS_RASTERS_PROBE.md)
i [przeglądarka](PAGES_BROWSER_PROBE.md). Parametry poniżej pozostają
hipotezami, a nie nowymi uzgodnieniami użytkownika.

Wartości do eksperymentów, **nie zatwierdzone gwarancje**:

| Parametr | Hipoteza do sprawdzenia |
| --- | --- |
| Automatyczne ładowanie planów | rozdzielczość mapy ≤1 m/px CSS |
| Minimalny rozmiar planu na ekranie | dłuższy bok ≥64 px CSS |
| Mały podgląd na poziomie | do 512 px |
| Kafle dużych planów | 256 lub 512 px |
| Aktywne zdekodowane obrazy | budżet 64 MiB |
| Równoległe pobrania obrazów | 6 |

Bok 64 px nie gwarantuje czytelności, a budżet obrazów nie jest pamięcią
całego procesu, GPU lub podkładów. Badane widoki wycentrowane na planach
nie dowodzą znalezienia najgęstszego możliwego widoku.
Propozycja przy zbyt małej skali: obiekty/zasięgi i komunikat o przybliżeniu.
**Uzgodnienie z 2026-10-30:** akcja „Pokaż cały plan” dopasowuje widok
do całego wybranego planu i zawsze pokazuje jego lekki podgląd, także
ponad progiem automatycznego ładowania. Szczegóły pojawiają się po
przybliżeniu. Wyjątek dotyczy jawnie wybranego planu, nie automatycznego
wczytania wszystkich planów w powiększonym zasięgu. Podgląd zachowuje
georeferencję; nie obiecuje czytelności wszystkich napisów w widoku całości.
Jego rozdzielczość i budżet nadal wymagają pomiaru, a próg 1 m/px pozostaje
hipotezą. Nie stosujemy arbitralnego limitu pierwszych 24 planów.
Zmiana widoku anuluje zbędne żądania, a ograniczony cache zwalnia zasoby.
Proponowane obniżanie rozdzielczości pod presją pamięci musi być jawne
i sprawdzone pod względem czytelności oraz nakładania wielu planów.

## Granice modułów — rekomendacja do przyszłej implementacji

Według `mattpocock-skills:codebase-design` proponowane są poniższe
moduły z małymi interfejsami. Nie tworzymy obecnie pełnej aplikacji,
ogólnego rejestru importerów ani abstrakcji dla nieużywanego COG.

| Moduł / interfejs | Ukryta złożoność i istotna powierzchnia testów |
| --- | --- |
| Wejścia przebiegu: `prepareInputs(run)` | Latest, tag→commit, trwałe przypięcia, sumy i bezpieczne rozpakowanie. Testy: zmiana Latest między/ podczas runów, Re-run bez manifestu, zmieniony asset, wadliwe archiwum. Trzy jawne czytniki źródeł. |
| Pakiet mapy: `buildPackage(inputs, profile)` | Import, relacje, transformacje i rastry, komplet plików oraz rozmiar strony. Testy wyników: osie, obrót/pół piksela, wiele otworów i wariantów, zachowanie źródłowych wartości, kompletność paczki. Bez audytu pomiarów. |
| Katalog: wyszukanie, szczegóły i jawne relacje migawki | Normalizacja polskich znaków, historia na żądanie i klucz `(object_id,id)`. Testy: powtarzające się lokalne ID pomiarów, odrzucone w szczegółach, brak relacji, opóźniona odpowiedź po zmianie wyboru. |
| Widok mapy i zasoby: stan widoku/warstw → gotowość/błędy | OpenLayers, wybór poziomów, anulowanie i cache, TPN/OSM. Testy rzeczywistej przeglądarki: wyjątek „Pokaż cały plan”, brak żądań spoza widoku, DPR, spóźnione odpowiedzi, luki/powrót, długa nawigacja. |
| Publikacja i ochrona: `applyOperation(operation, package)` | Kolejność deploy/rollback, ewidencja i retencja. Testy obserwowalnych stanów: A→B→A, stary build po rollbacku, wersja bieżąca przez 60+ dni, przerwanie na etapach zapisu/deployu, ochrona unknown. |

To rekomendacja techniczna autora, nie uzgodnienie nazw modułów ani
ostatecznych granic testów. TDD istotnych zachowań zacznie się po zgodzie
na implementację i uzgodnieniu tych granic. Zewnętrzne efekty GitHub
i renderer mają rzeczywiste miejsca podmiany/testowania; nie opakowujemy
każdego endpointu osobną warstwą. Wynik sondy nie jest testem produkcyjnego
modułu. Testy z atrapą API nie zastępują integracji z GitHub.

## Publikacja, manifest i ręczne cofnięcie

Normalne wdrożenie 2D uruchamia wyłącznie `workflow_dispatch` w nowym repo.
Build i testy poprzedzają osobny job publikujący kompletną paczkę.
Błąd pobrania, formatu, przetwarzania, testów lub buildu zatrzymuje
publikację i zachowuje poprzednią działającą stronę.

### Run workflow i Re-run jobs

Rekomendacja techniczna: pierwszy wybór wejść zostaje zapisany przed ich
pobraniem jako nieprzepisywany artefakt `inputs-<run_id>`, z retencją
90 dni. `Re-run all jobs`, `Re-run failed jobs` i ponowienie pojedynczego
joba korzystają z tego samego manifestu. GitHub zachowuje `run_id`,
`GITHUB_SHA` i `GITHUB_REF`; zmienia `run_attempt`. Brak zapisanego
manifestu, również po awarii jego pierwszego zapisu, zatrzymuje ponowienie
z komunikatem „Uruchom nowe Run workflow”. **Re-run nigdy nie odczytuje
ponownie Latest.** Nowe Run workflow zawsze ponownie odczytuje Latest
i wybiera aktualne wejścia; nie dziedziczy przypięcia poprzedniego runu.
Jeśli źródło nie opublikowało nowego wydania, jego wybór może pozostać
ten sam. Przykładowo nowe Latest tylko Georeferencera wystarcza do
wdrożenia migawki z nowymi planami i dotychczasowymi Latest GPS oraz JKTZ.

Gotowa i zarchiwizowana paczka tego przebiegu jest ponownie używana po
sprawdzeniu sum. Nie nadpisujemy jej inną zawartością pod tym samym ID.
Jeśli build wcześniej nie ukończył paczki, można ponowić przetwarzanie
z przypiętych wejść. Niedostępny przypięty asset lub niezgodny digest
powoduje błąd; nie dobieramy zamiennika po nazwie. Artefakt transportowy
Pages może być tworzony na nowo z tej samej gotowej paczki dla kolejnego
`run_attempt`; nie stanowi archiwum rollbacku.

Pobieranie może ponowić tę samą operację po przejściowym błędzie sieci,
429 lub 5xx, z ograniczoną liczbą prób, opóźnieniem i respektowaniem
`Retry-After`. Błąd formatu lub sumy nie uruchamia automatycznej zmiany
wejść ani pomijania pliku. Szczegółowe limity są wyborem implementacyjnym.

Manifest zapisuje repozytoria, release/tag/commit/asset ID, URL, daty,
SHA-256 wejść i wyników, commit aplikacji, wersje narzędzi, parametry
przekształceń i raport techniczny. Hash pobranego pliku trzeba odróżniać
od porównania z oczekiwaną sumą opublikowaną przez źródło. Kontrakt sum
kontrolnych opisuje sekcja kontraktów wejść.

Rekomendacja doprecyzowana 2026-10-31: niezmienne przypięcia wejść i późniejszy
manifest wyniku są osobnymi dokumentami. Nie dopisujemy wyników walidacji
do artefaktu `inputs-<run_id>` po jego zapisaniu. Paczka zawiera oba;
zapis przypięć wymaga odczytu potwierdzającego kompletność. Szczegóły
retencji, ponowień i aktualnego API: [badanie publikacji](PAGES_PUBLICATION_RESEARCH.md).

Po publikacji test działającego adresu raportuje błąd w wyniku workflow.
**Nie uruchamia automatycznego cofnięcia.** Błąd wykryty dopiero po
wdrożeniu może pozostać widoczny do reakcji użytkownika. Awarię podkładu
trzeba odróżnić od awarii aplikacji.

### Archiwum gotowych paczek

Osobny ręczny workflow przywraca gotową paczkę z manifestem, bez ponownego
wybierania Latest i bez ponownego buildu:

- Bieżącą paczkę zachowujemy przez cały czas używania wersji.
- Zastąpiona paczka jest dostępna przez **15 dni od zastąpienia**,
  a nie od daty pierwotnego zbudowania.
- Nie wymagamy bezterminowego archiwum wszystkich surowych wejść ani
  deduplikowanego zewnętrznego magazynu. Po upływie okna nie gwarantujemy
  odtworzenia dawnego wdrożenia.
- Samo `retention-days: 15` przy pierwotnym buildzie nie spełnia kontraktu.
  Rekomendacja techniczna: gotowa paczka i manifest jako zasoby wydania
  `pages-<run_id>` nowego repo mapy, bez oznaczania go jako Latest produktu.
  Nie są to wydania trzech repozytoriów źródłowych. Paczki nie trafiają
  do historii Git. Właściwa retencja nie zależy od wygaśnięcia artefaktu Actions.
- Jeden mały plik ewidencji na technicznej gałęzi nowego repo przechowuje
  bieżącą paczkę, daty zastąpienia, ostatnią zakończoną operację i ewentualną
  niedokończoną operację. Zapis wymaga poprzedniego SHA pliku; konflikt
  zatrzymuje operację. Nie jest potrzebna baza ani zewnętrzny magazyn.
- Przywrócona paczka ponownie staje się bieżąca. Po kolejnym zastąpieniu
  otrzymuje nowe pełne 15 dni. Błąd buildu nie zastępuje bieżącej wersji
  i nie uruchamia jej okresu 15 dni.
- Sprzątanie może nastąpić po kolejnym ręcznym deployu/rollbacku. Okno
  oznacza minimalną dostępność, nie obowiązek usunięcia dokładnie w 15. dniu;
  nie potrzeba osobnego harmonogramu. Bieżące i niejednoznaczne paczki
  są zawsze chronione, a przy błędzie odczytu ewidencji nie usuwamy niczego.

### Współbieżność i przerwane operacje

Finalne joby deployu i rollbacku oraz sprzątanie mają wspólną stałą grupę
concurrency, np. `pages-production`, z `cancel-in-progress: false`.
Rekomendowane `queue: max` zachowuje oczekujące operacje zamiast kasować
wcześniejszy oczekujący rollback. Buildy mogą biec równolegle, ale zmiana
strony i ewidencji jest szeregowa. Kolejność wejścia do grupy nie dowodzi
kolejności uruchomienia workflow.

W zatwierdzonej próbie GitHub dwa runy pozostały jednocześnie `pending`
za trwającym B; po jego anulowaniu oba dotarły do wykonania i zatrzymały
się przed deployem z powodu nieuzgodnionego `pending` ewidencji.
To dowód zachowania tej kolejki i blokady, bez testu limitu 100 operacji
ani zmian administracyjnych poza workflow. [Dziennik próby](PAGES_PUBLICATION_GITHUB_TRIAL.md).

Pod blokadą porównujemy pierwotne `created_at` operacji z ostatnią zakończoną
publikacją/rollbackiem. Starszy przebieg kończy się jawnym „pominięto —
zastąpiony nowszą operacją”, bez publikacji. `run_id` nie jest udokumentowanym
licznikiem czasu, a `run_number` nie porównuje dwóch różnych workflow.
Równy czas i różne ID są niejednoznaczne: nie publikujemy, podajemy powód.
To samo ID oznacza wznowienie lub operację bez zmian, nie nowe wdrożenie.
Rollback ma nowy czas operacji, mimo że przywraca starszą paczkę; dawny
build nie może następnie nadpisać świadomego rollbacku.

Kolejność finalnej operacji:

1. Uzgodnij ewentualną poprzednią niedokończoną operację i sprawdź kolejność.
2. Zweryfikuj archiwum bieżącej wersji oraz kompletną nową paczkę i sumy.
3. Zapisz stan `pending`, wskazujący obie chronione paczki i tożsamość operacji.
4. Wdróż i odczytaj wynik wdrożenia Pages.
5. Po potwierdzonym sukcesie zmień bieżącą paczkę i zapisz czas zastąpienia
   poprzedniej. Jeśli dokładny czas zastąpienia jest nieznany, późniejszy
   czas potwierdzenia może jedynie wydłużyć ochronę, nigdy ją skrócić.
6. Wykonaj test działającego adresu i sprzątanie bez skracania ochrony.

Publikacja i zapis ewidencji nie są jedną transakcją. Timeout nie dowodzi
niepowodzenia publikacji. Po przerwaniu `pending` chroni obie paczki;
wznowienie uzgadnia status wdrożenia z identyfikatorem paczki w manifeście
strony. Przy sprzecznym/nieznanym wyniku zatrzymuje dalszą publikację
i sprzątanie, zachowując paczki. Błąd testu adresu po potwierdzonym deployu
nie zmienia historii zastąpienia i nie powoduje automatycznego rollbacku.

**Odzysk — potwierdzony zakres i pozostałe ryzyko, 2026-10-31:** sprawdzone
`actions/deploy-pages` v5.0.1 nie ma outputu deployment ID; `page_url`
powstaje przed końcowym sukcesem. SHA aplikacji także nie identyfikuje
jednoznacznie wdrożenia danych lub rollbacku. Sprawdzona ścieżka używa
`pending`, który utrwala `run_id`, `run_attempt`, numeryczne ID joba,
head SHA oraz numer i nazwę kroku;
po przerwaniu **po ukończeniu kroku deploy** Actions Jobs API potwierdza
sukces tego konkretnego kroku, a odczyt strony zgodność paczki. Dopiero
wtedy uzgadniamy ewidencję. Bez `continue-on-error` na kroku publikacji.

W [próbie GitHub](PAGES_PUBLICATION_GITHUB_TRIAL.md) B anulowano podczas
pauzy po udanym kroku 6. Mimo anulowanego joba historia tego kroku
zachowała `success`; jawny odzysk potwierdził jego tożsamość, oba archiwa
i publiczne bajty B, po czym uzgodnił ewidencję bez nowego deployu.
Powtórny odzysk nie przesunął czasu ochrony. To test anulowania runu
po sukcesie kroku, nie twardego zabicia runnera.

Przerwanie **wewnątrz kroku**, timeout/cancel bez potwierdzonego sukcesu,
brak historii lub sprzeczny
odczyt pozostają `unknown`: obie paczki chronione, dalsza publikacja
i usuwanie zatrzymane do rozpoznania. Nie ponawiamy POST w ciemno.
Próba nie daje gwarancji odzyskania tych przypadków. Potwierdzona awaria
przed publikacją nie uruchamia
retencji poprzedniej wersji. [Kod, API i scenariusze](PAGES_PUBLICATION_RESEARCH.md).

### Limity publikacji i źródła kontraktu

GitHub ogranicza opublikowaną stronę do **1 GB**, wdrożenie do **10 minut**,
a transfer ma miękki limit **100 GB/miesiąc**. Większy dopuszczalny artefakt
transportowy Pages nie podnosi limitu strony. Release asset musi mieć
mniej niż 2 GiB; suma plików strony, ZIP/TAR i transfer przeglądarki
są trzema różnymi wielkościami.

Build raportuje pełny rozmiar publikacji przed deployem i zatrzymuje się
po przekroczeniu limitu. Nie ogranicza po cichu katalogu planów ani ich
szczegółowości. Pełna piramida z podglądami została zmierzona 2026-10-31
(275 282 006 B); pełna strona nie istnieje i jej rozmiar pozostaje do pomiaru. Brak miejsca
wymaga zmiany sposobu kodowania/pakowania i ponownego sprawdzenia jakości;
nie jest podstawą obietnicy, że obecna propozycja zmieści się na Pages.

Oficjalne źródła sprawdzone 2026-10-30:
[limity Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits),
[workflow Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases),
[retencja artefaktów](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization),
[Re-run](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs),
[zmienne runu](https://docs.github.com/en/actions/reference/workflows-and-actions/variables),
[concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
[zapis ewidencji](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents),
[API wdrożeń](https://docs.github.com/en/rest/pages/pages#create-a-github-pages-deployment),
[deploy-pages](https://github.com/actions/deploy-pages).

TPN/OSM nie należą do odtwarzalnej migawki. Cofnięcie strony nie przywraca
historycznych odpowiedzi zewnętrznych podkładów.

## Kryteria odbioru i dowody

- Importery: brak pliku lub składowej SHP, nieobsługiwany schemat,
  uszkodzone archiwum, niezgodna oczekiwana suma, nieobsługiwany CRS,
  błąd przetwarzania. Bez ponownego audytu źródeł.
- Wybór wejść: przypięcie raz na początku, odrzucenie draft/prerelease,
  brak zmiany zasobów po pojawieniu się nowego Latest w trakcie runu
  lub przed jego Re-run. Osobny scenariusz: po wdrożeniu A ukazuje się
  nowe Latest jednego źródła; kolejne Run workflow wybiera je i wdraża B,
  zachowując aktualne Latest pozostałych źródeł.
- Transformacje: punkty kontrolne GDAL/PROJ, brak zamiany osi,
  przesunięcia o pół piksela i utraty obrotu przez kod mapy.
- Interfejs: wyszukiwanie, dostępne pomiary, przełączniki, wybór i nakładanie
  planów, przezroczystość, klawiatura i dotyk.
- Sieć i pamięć: brak automatycznie ładowanych obrazów planów przed
  ustalonym progiem i spoza widoku; uzgodniony wyjątek podglądu wybranego
  planu po „Pokaż cały plan”,
  ograniczenie pobrań i zwalnianie zasobów podczas dłuższej nawigacji.
- Statyczny build: docelowy prefiks URL Pages, bez serwera deweloperskiego,
  lokalnych ścieżek, proxy i niejawnych usług.
- Publikacja: błędy przed deployem blokują job publikujący; osobne testy
  nieudanej publikacji, równoległych przebiegów i rollbacku, także gdy
  poprzednia wersja działała dłużej niż 15 dni.
- Przeglądarki: Chromium, Firefox, Safari/WebKit oraz **rzeczywiste
  Android/Chrome i iPhone/Safari**. Zimny start w nowym profilu, interfejs,
  TPN/OSM, granice pokrycia i dłuższa trasa przez gęste obszary.
  Emulacja viewportu/CPU nie zastępuje telefonu. Odbiór pierwszej wersji
  nie dodaje ręcznego etapu do każdego późniejszego wdrożenia.
- Raport: transfer, definicja gotowości, czasy klatek i metoda pomiaru
  pamięci z ograniczeniami JS heap/RSS/GPU; sprzęt, przeglądarka, DPR,
  sieć, zimny/ciepły cache i osobno koszt podkładów.

Wcześniejsze **cele do weryfikacji**, nie wyniki ani obietnice: aplikacja
i indeksy do 1 MB transferu, gotowość do 3 s przy 10 Mb/s, p95 klatki
do 33 ms na komputerze referencyjnym. Trzeba określić moment gotowości,
urządzenia i kryteria mobilne. Pomiar jednego obrazu lub pustej mapy
nie zastępuje pomiaru kompletnej aplikacji.

Plan pomiarów doprecyzowuje dwa oddzielne momenty: gotowość interfejsu
(działają wyszukiwanie, przesuwanie i wybór obiektu) oraz gotowość widoku
(wymagane w danej skali warstwy bieżącego widoku zostały narysowane,
a braki mają jawny stan błędu). Podkłady zewnętrzne i plany należy raportować
osobno; wcześniejszy cel 3 s nie staje się automatycznie limitem któregokolwiek
z tych pomiarów. Dalszy plan odbioru obejmuje zimny start, Miętusią w całości
i w szczególe, drobne napisy, kilka nałożonych planów, gęsty obszar oraz
powrót do wcześniejszych miejsc po dłuższej nawigacji.

Na iPhonie 14 Pro należy sprawdzić także zmianę orientacji ekranu,
ukrycie/powrót do karty, stabilność i ewentualne przeładowanie karty przez
system. JS heap, suma buforów rastrów i obserwacja stabilności nie są
pomiarem pełnej pamięci. Jeśli narzędzia nie pozwolą zmierzyć procesu
przeglądarki i kosztu GPU, raport zachowuje ten brak; nie wyprowadza
całkowitej pamięci telefonu z limitu 64 MiB dla obrazów.

## Stan dopracowania i zależności decyzji

Runda z 2026-10-30 i jej doprecyzowanie zapisały ustalenia użytkownika:

1. „Pokaż cały plan” pokazuje podgląd całości, szczegóły po przybliżeniu.
2. Użytkownik wykona test na swoim iPhonie 14 Pro.
3. Wszystkie nazwy Best pozostają widoczne, także przy kolizjach.
4. Każde nowe Run workflow ponownie sprawdza Latest i wdraża nowsze
   wydania, jeśli się pojawiły; wystarczy zmiana jednego źródła.

Pozostałe uzupełnienia techniczne są rekomendacjami opartymi na wskazanych
źródłach. Nie stanowią zatwierdzenia całej specyfikacji ani zgody na pełną
implementację aplikacji. Użytkownik osobno dopuścił lokalne sondy,
publikację konkretnej sondy TPN, zapis dokumentacji i sond w repo oraz
[ograniczoną próbę publikacji i odzysku na GitHubie](PAGES_PUBLICATION_GITHUB_TRIAL.md).
Pełna aplikacja i produkcyjny workflow wymagają osobnego uzgodnienia.

| Gałąź projektu | Co już ustalono/sprawdzono | Zależność i sposób zamknięcia |
| --- | --- | --- |
| TPN → EPSG:2180 | Zatwierdzona sonda opublikowana na Pages; publiczne pliki zgodne z paczką; cztery podkłady w Chromium/WebKit, negatywne kontrole CORS/DataTile, OSM w pojedynczej luce | Dokładny stan silników w raporcie przeglądarki; natywne Safari i rzeczywiste telefony nadal niewykonane. WebKit desktop nie zalicza iPhone'a. |
| Importery i pochodzenie | Ponownie pobrane bieżące wydania, sumy i przypięte metadane; pięć wad odrzuconych przez sondę | Produkcyjne importery i pełne testy ich kontraktu dopiero po zgodzie na implementację. Bez audytu pomiarów. |
| Plany i rozmiar strony | Pełny wariant WebP512 + podglądy: 275,28 MB; 20/20 prób OL dla pięciu planów przy DPR1/3 | Rekomendacja autora: WebP512. Pozostają szwy/gutter, nakładanie, zarządzanie zasobami, cały rozmiar strony i CI. Brak obecnej potrzeby COG. |
| Czytelność | Wszystkie nazwy Best, bez ukrywania kolizji | Sprawdzić gęste widoki i wybór obiektu, zachowując decyzję. Układ panelu mobilnego pozostaje propozycją. |
| Odbiór mobilny | iPhone 14 Pro wskazany; Android/Chrome nadal wymagany | Wskazać rzeczywisty Android; ustalić mierzalne progi po próbie referencyjnej. Brak urządzenia/pomiaru pozostaje brakiem dowodu. |
| Jedno kliknięcie / Re-run | Nowy klik sprawdza aktualne Latest i wdraża dostępne nowe wydania; przypięcie i trwały manifest dotyczą pojedynczego runu oraz jego Re-run | Nowe Latest jednego źródła między kliknięciami; zmiana Latest podczas runu i przed Re-run; błędy zapisu, brak assetu i niezgodna suma. |
| Publikacja i rollback | Na GitHubie potwierdzono A→B→A, kolejkę, blokadę `pending`, odzysk po anulowaniu za udanym krokiem deployu, idempotentny powtórny odzysk i pominięcie starego B po rollbacku. Przywrócono oryginalną paczkę i ustawienia Pages; workflow próby wyłączono. | Długotrwała retencja, twardy kill, unknown wewnątrz POST i kasowanie nadal bez dowodu integracyjnego. To nie test Latest ani pełnego workflow danych. |

### Kryteria gotowości do dalszych prac

- Dokument jest podstawą zaplanowania ograniczonych prób technicznych;
  **nie potwierdza jeszcze wykonalności wszystkich wymagań**. Lokalne
  próby techniczne wykonano na podstawie rozszerzonej zgody z 2026-10-31;
  ich wyniki nie zastępują odbioru. Minimalną paczkę TPN następnie
  zatwierdzono i opublikowano na publicznym Pages. To nadal sonda techniczna.
- Dowód renderowania TPN na docelowym hostingu uzyskano dla badanych
  silników desktopowych. Potwierdzono także odzysk po anulowaniu runu
  za ukończonym krokiem deployu, rollback i blokadę starego runu. Próbę
  zakończono odczytem przywróconej oryginalnej paczki i ustawień Pages.
  Pełna implementacja wymaga osobnej zgody. Próby
  uzasadniają format WebP512 jako rekomendację; jakość brzegów i gęstych
  widoków oraz pełny rozmiar strony nadal wymagają weryfikacji.
  Każdy wynik ma zawierać warunki testu i ograniczenia.
- Progi pamięci/czasu i układ panelu nie stają się wymaganiami wyłącznie
  dlatego, że wpisano propozycję do dokumentu. Wynik próby powinien
  umożliwić ich świadome ustalenie; nie wolno obiecać 3 s na telefonie
  na podstawie wcześniejszego testu jednego obrazu.
- Przed odbiorem wersji produkcyjnej muszą zostać wykonane scenariusze
  desktopowe, iPhone 14 Pro i Android/Chrome oraz testy błędów importu,
  publikacji i rollbacku. Nie można zaliczyć brakującego testu przez
  pomyślny fallback, emulację albo brak zauważonej awarii.

## Próbki źródeł i materiały porównawcze

Rozpoznanie z 2026-10-30 — **wersje i liczebności nie są przypięciem buildu**:

- JKTZ `v1.4.12`: ZIP około 22 MB, 73 eksporty modeli i eksport zbiorczy,
  źródłowy CRS eksportów EPSG:32634.
- GPS `v1.3.2`: SQLite z 1028 obiektami, 1019 jaskiniami i 1934 pomiarami,
  w tym 4 odrzuconymi; osobne eksporty Best.
- Georeferencer `v0.7.4`: 814 planów, GeoTIFF/TFW, manifest i metadane,
  źródłowy GPS `v1.3.2` oraz oznaczenia niepewności.

[Pomiary i ograniczenia](PAGES_MAP_PERFORMANCE.md),
[analiza QGIS WASM i COG](QGIS_WASM_RESEARCH.md).
Raporty zachowują dowody wcześniejszych prób; raport przeglądarki obejmuje
także publiczną sondę TPN. Żaden nie stanowi odbioru pełnej aplikacji.

Dokumentacja odniesienia:
[OpenLayers](https://openlayers.org/doc/tutorials/raster-reprojection.html),
[OSM](https://operations.osmfoundation.org/policies/tiles/),
[GitHub Latest](https://docs.github.com/en/rest/releases/releases#get-the-latest-release),
[Pages i osobne repozytoria](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages),
[wdrażanie artefaktów](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[retencja artefaktów Actions](https://docs.github.com/en/actions/tutorials/store-and-share-data).
