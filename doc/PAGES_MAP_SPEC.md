# Mapa JKTZ 2D — specyfikacja pierwszej wersji

Aktualizacja: 2026-10-31. Użytkownik upoważnił do domknięcia specyfikacji
i pełnej implementacji. **Zmiana działających publicznych Pages wymaga
osobnej zgody.** Poniższy kontrakt zastępuje wcześniejsze ograniczenie
prac do dokumentacji i sond. Plan realizacji i obsługa: [IMPLEMENTATION.md](IMPLEMENTATION.md).

Podstawą techniczną są wykonane próby: [przeglądarka i TPN](PAGES_BROWSER_PROBE.md),
[wejścia i pełny katalog rastrów](PAGES_INPUTS_RASTERS_PROBE.md) oraz
[publikacja na GitHubie](PAGES_PUBLICATION_GITHUB_TRIAL.md). Raporty opisują
historyczne próby, nie odbiór gotowej aplikacji. Nie rozpoczynamy kolejnej
rundy badań publikacji ani ogólnego systemu automatycznego odzyskiwania.

## Zakres i granice

Polska, statyczna mapa pozycji obiektów, dostępnej historii pomiarów,
ciągów JKTZ i planów Georeferencera. Użytkownik może wyszukać obiekt,
porównać źródła oraz sprawdzić pochodzenie i niepewność danych. Pierwsza
wersja obejmuje **cały dostępny katalog trzech źródeł**, nie próbki.

- Osobne repozytorium: [dlubom/jktz-mapa](https://github.com/dlubom/jktz-mapa).
  Build nie wymaga lokalnych checkoutów sąsiednich repozytoriów.
- Istniejące CaveView 3D JKTZ, jego adres, wygląd i publikacja pozostają
  bez zmian. Nie przenosimy go pod `3d/`, nie tworzymy wspólnej paczki.
- README pozostaje bez nowych informacji i linków do Pages.
- Silnik mapy: **OpenLayers 10.11.0**; TypeScript, Vite i proj4js, bez
  frameworka UI i serwera aplikacji. Python oraz GDAL/PROJ przygotowują dane.
  QGIS WASM i COG pozostają poza pierwszą wersją.
- Mapa używa migawki z buildu. Przeglądarka nie odpytuje GitHub Latest.
  TPN i OSM są zewnętrznymi podkładami pobieranymi podczas oglądania.
- Odbiór docelowy obejmuje komputer, Android/Chrome i iPhone/Safari.
  Brak fizycznego telefonu nie blokuje implementacji ani lokalnego podglądu;
  niewykonane testy urządzeń pozostają jawnie do odbioru. Użytkownik
  zadeklarował iPhone 14 Pro; wersję iOS/Safari zapisujemy przy teście.

## Dane, współrzędne i niepewności

Walidacja jest techniczna: integralność, obsługiwane schematy, wymagane
składowe i pola, CRS oraz możliwość odczytu i przetworzenia. Nie wykonujemy
ponownego audytu pomiarów, wyboru Best, orientacji planów ani kompletności
powiązań katalogowych. Nie poprawiamy źródeł i nie dopisujemy informacji.
Liczebności z wcześniejszych prób nie są stałymi walidatora.

- Widok, podziałka i odczyt współrzędnych: **EPSG:2180**, metry.
  Etykiety `X — północ`, `Y — wschód`; wewnętrzny porządek OpenLayers
  to easting/northing. Sam odczyt przeliczony z widoku EPSG:3857 nie wystarcza.
- Reprojekcja tworzy dane pochodne. Zachowujemy oryginalne współrzędne,
  CRS, Z/datum, transformacje rastrów i źródłowe metadane. Rzut 2D nie usuwa Z.
- Ciągi pochodzą z eksportów wybranego wydania JKTZ; nie kompilujemy ich
  ponownie z aktualnym GPS. Nie przesuwamy planów do nowego Best.
- Relacje wynikają wyłącznie z jawnych ID i mapowań źródłowych, także
  dla systemów wielu jaskiń i otworów. Nie zgadujemy po nazwie lub geometrii.
  Brak mapowania pozostaje widoczny jako brak dostępnej relacji.
- Brak opcjonalnej informacji nie zatrzymuje buildu. Uszkodzona struktura,
  np. zduplikowany klucz lub Best wskazujący nieistniejący pomiar danego
  obiektu, zatrzymuje importer.
- Best oznacza wybór katalogu, nie potwierdzenie pomiaru GNSS ani znanej
  dokładności. Rozrzut punktów nie jest miarą dokładności. Techniczny autor
  importu nie staje się autorem pomiaru.
- Georeferencja uwzględnia wszystkie sześć współczynników transformacji,
  obrót oraz konwencję środka/narożnika piksela. Prostokąt zasięgu nie
  zastępuje transformacji. `unknown/unverified` pozostaje niezweryfikowane.

## Kontrakty wejść

Każdy nowy Run workflow odczytuje GitHub **Latest** dla:

1. `dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich`,
2. `dlubom/gps-kataster-obiektow-tatr`,
3. `dlubom/Georeferencer`.

Wskazanie Latest jest wiążące także dla pozornie starszego tagu;
nie sortujemy samodzielnie po SemVer ani dacie. Sprawdzamy `draft=false`
i `prerelease=false`, rozwiązujemy tagi annotated do commitów i zapisujemy
konkretne asset ID przed pobieraniem. `target_commitish` nie jest przypięciem
commitu. Brak wymaganego assetu lub nieobsługiwany format zatrzymuje run;
nie wybieramy starszego wydania. Trzy odczyty są sekwencją przypięć,
nie transakcją wspólnego momentu wydania.

Dla release assets wymagany jest oczekiwany `sha256:` z API. Zapisujemy
osobno oczekiwaną sumę, hash pobranych bajtów i wynik porównania. Samo
wyliczenie własnej sumy nie zastępuje kontroli integralności. Uzupełnienia
pobieramy z dokładnego commitu wydania; zapisujemy ścieżkę i hash treści.
Git blob SHA nie jest SHA-256. Archiwa rozpakowujemy z kontrolą ścieżek,
duplikatów i limitów, bez wykonywania zawartości.

Przykładowe wersje, sumy i rozmiary z rozpoznania są w
[raporcie wejść](PAGES_INPUTS_RASTERS_PROBE.md); nie przypinają przyszłych runów.

### JKTZ

- Asset `JKTZ-{tag}.zip`; modele `exports/caves/{model_id}` z kompletem
  `.shp`, `.shx`, `.dbf`, `.prj`. `.cpg` jest opcjonalne. Obsługiwany profil:
  PolyLineZ (typ 13), EPSG:32634. Zachowujemy Z.
- Modele importujemy osobno. `exports/JKTZ-{tag}-all.*` jest alternatywą,
  nie kolejną kopią ciągów do nałożenia.
- DBF nie zawiera `object_id`. ID modelu odpowiada prefiksowi stacji przed
  pierwszym `:` według eksportera źródłowego.
- Jawne relacje odczytujemy jako dane z `gps_fix(station, object_id)`
  w `Poligony/OTWORY.SRV.j2` z przypiętego commitu; pliku nie ma w ZIP-ie.
  Nie wykonujemy szablonu; zakomentowane wywołania nie są relacjami.
  Szablon nie gwarantuje kompletności otworów systemu.
- Brak wersjonowanego manifestu paczki: importer sprawdza jawny profil
  układu, składników SHP i CRS. Zmiana wymaganego układu zatrzymuje import.

### GPS

- `katalog.sqlite.zip` z `katalog.sqlite` oraz `metadata.json`.
  Best CSV/GeoJSON lub SHP nie zastępują bazy dostępnej historii.
- Obsługiwane: `metadata_schema_version=1`, `data_schema_version=1`
  i tekstowe `schema_version="1"` w tabeli `metadata`.
- Tabele: `objects`, `caves`, `measurements`, `best_measurements`,
  `object_external_refs`, `cave_external_refs`, `relations`, `attachments`,
  `metadata`. `validation_flags` pozostają informacją źródła.
- Klucz pomiaru: **`(object_id, id)`**. Best wskazuje pomiar w obrębie
  obiektu. Zachowujemy geometrię, Z/datum, dokładność, daty, źródła,
  metodę, urządzenie, autorstwo, statusy, notatki i tagi, o ile istnieją.
- `x_1992` to północ, `y_1992` to wschód; `geom_1992` ma postać
  `POINT(y_1992 x_1992)`. WGS84: `POINT(lon lat)`.
- `objects.cave_id`, `caves.object_ids_json`, `system_name` i referencje
  rozróżniają obiekt, jaskinię i system. ID otworu nie jest automatycznie
  identyfikatorem PIG. Nie rekonstruujemy aliasów z luźnych notatek.
- Załączniki zachowują m.in. `kind`, `path`, `caption`. Lokalna ścieżka
  nie dowodzi dostępności pliku: nie tworzymy z niej niedziałającego URL.

### Georeferencer

- Asset `geotiff-tatry-{tag}.zip`; manifest `schema_version=1`,
  `status="complete"`, `content_version="t10-content-v1"`,
  `release.version="t11-v2"`, geometria `t06-local-similarity-v1`.
- `release.files[]` wiąże `plan_id`, `output`, `archive_path`, `sha256`.
  Nie odgadujemy ID z nazwy TIFF-a. Weryfikujemy sumy wszystkich składowych.
- Zachowujemy `dir_id`, `measurement`, `inputs`, `outputs`, `acceptance`,
  `parameters`, `orientation`, `coordinate_source` i dostępne uzupełnienia.
  Obsługiwany TIFF: EPSG:2180, jeden kanał 1-bitowy, CCITT Group 4.
  Wymiary i geotransformacja muszą odpowiadać `acceptance`.
- ZIP zawiera TIFF-y, manifest i `metadane/{plan_id}/image.tfw`,
  `computed.json`; nie zawiera `meta.yaml`, `source.json`, `image-identity.json`.
  `data/caves/{dir_id}/meta.yaml` pobieramy z commitu wydania i porównujemy
  z `plans[].inputs["meta.yaml"]`. Dostępne opcjonalne uzupełnienia pobieramy
  z tego samego commitu; brak pozostaje brakiem.
- `cave.source_cave_id` jawnie wiąże wariant z jaskinią. `dir_id` ani ID
  obrazu nie muszą należeć do przestrzeni PIG. `source_directory` z manifestu
  nie jest zależnością lokalną buildu.
- Licencje i autorstwo planów pochodzą z dostępnych metadanych; nie
  dziedziczą automatycznie licencji GPS/JKTZ. Brak deklaracji jest jawny.

## Interfejs i warstwy

Mapa wypełnia okno. Na komputerze panel boczny, na małym ekranie panel
dostosowany do obsługi dotykiem; jego zwinięcie odsłania mapę. Panel mieści
wyszukiwanie, warstwy, wybrany obiekt, plany i źródła. Zachowujemy fokus
klawiatury, etykiety kontrolek, czytelne symbole i stany ładowania/błędu.
Przewijanie długiej historii lub katalogu nie blokuje dostępu do mapy.

| Warstwa | Stan początkowy |
| --- | --- |
| Best — wybrane pozycje obiektów | Włączona, z nazwami |
| Pozostałe pomiary GPS/katalogowe | Wyłączona; bez Best i odrzuconych |
| Pomiary odrzucone | Wyłączona |
| Linie różnic względem Best | Wyłączona; pozioma różnica w metrach |
| Ciągi JKTZ | Włączone; przełączniki poszczególnych modeli |
| Plany Georeferencera | Włączone; krycie 75%, ładowanie według skali i widoku |

**Wszystkie nazwy Best w bieżącym widoku pozostają widoczne**, nawet gdy
się nakładają. Brak grupowania lub automatycznego ukrywania kolizji.
Wybrany obiekt może być wyróżniony, lecz nie usuwa pozostałych nazw.
Przy kilku trafieniach kliknięcia/tapnięcia użytkownik może wybrać obiekt.

Wyszukiwanie toleruje wielkość liter i brak polskich znaków; obejmuje
nazwy i dostępne identyfikatory obiektów/jaskiń oraz dostępne nazwy systemów.
Plany i modele bez powiązania z GPS pozostają dostępne we własnym katalogu.
Brak wyników ma jawny komunikat. Wybór wyniku przybliża mapę i otwiera
szczegóły; nie wyłącza pozostałych warstw.

Szczegóły obejmują wszystkie pomiary migawki, także odrzucone i ukryte
na mapie, oraz uzasadnienie Best. „Historia” oznacza dostępne rekordy,
nie rekonstrukcję dawnych edycji lub wyborów Best, których eksport nie
zawiera. Nieznane wartości pozostają nieznane. Relacje prowadzą do
powiązanych otworów, modeli i wariantów planów. Źródła udostępniają
wydania, commity, autorstwo, licencje i niepewności. Historia i obszerne
metadane mogą być wczytywane po wyborze; spóźniona odpowiedź nie może
nadpisać nowszego wyboru. Błąd pobrania ma możliwość ponowienia.

## Plany: wybór, całość i szczegół

Przyjęty format: **WebP lossless, podgląd do 512 px i kafle 512 px**.
GDAL przygotowuje pochodny raster north-up EPSG:2180 z pełnej transformacji
źródła; oryginalna transformacja pozostaje w metadanych. Białe tło skanu
jest zachowane, alfa obejmuje obszar poza skanem. Nie zwiększamy
rozdzielczości ponad źródło i nie dekodujemy całych wielkich TIFF-ów
w przeglądarce. Brzegowe kafle nie mogą rozciągać obrazu ani tworzyć szwów.

Ustawienia pierwszej implementacji, podlegające weryfikacji na gotowej mapie:

| Parametr | Wartość |
| --- | --- |
| Automatyczne ładowanie planów | rozdzielczość mapy ≤1 m/px CSS |
| Minimalny rozmiar automatycznie wczytanego planu | dłuższy bok ≥64 px CSS |
| Podgląd całości | do 512 px, bez zwiększania rozdzielczości |
| Kafle szczegółu | 512 px; poziom według m/px CSS i DPR |
| Równoległe pobrania obrazów planów | najwyżej 6 |
| Zdekodowane obrazy planów | ograniczony budżet 64 MiB, bez obietnicy limitu całego procesu |

Parametry te są wyborem implementacyjnym, nie gwarancją czasu, pamięci
telefonu ani czytelności każdego napisu. Przy zbyt małej skali mapa
pokazuje obiekty/zasięgi i informację o przybliżeniu. Nie stosujemy limitu
„pierwszych 24 planów”. Pod presją budżetu można jawnie wyświetlić
podgląd zamiast szczegółu; nie wolno po cichu zgubić wybranego planu.

- Lista umożliwia niezależny wybór wielu planów, nakładanie, zmianę
  kolejności góra/dół oraz osobne krycie. Wybór nie wyłącza innych planów.
  Ręcznie ukryty plan nie wraca przez automatyczne ładowanie.
- **„Pokaż cały plan”** włącza i dopasowuje widok do wybranego planu oraz
  zawsze wczytuje jego lekki podgląd, także powyżej progu automatycznego.
  Nie uruchamia przez to wszystkich planów w nowym zasięgu. Drobne napisy
  mogą wymagać przybliżenia; szczegół pojawia się po zbliżeniu.
- Ładowanie automatyczne obejmuje wyłącznie bieżący widok. Zmiana widoku
  anuluje niepotrzebne żądania, usuwa zbędne warstwy i zwalnia cache.
  Wyłączenie warstwy lub planu zwalnia jego zasoby. Brak obrazu ma jawny
  stan błędu i ponowienie; inne plany i obiekty nadal działają.

## Podkłady

Domyślnie **TPN RGB 2020**, z OSM przy oddaleniu i poza pokryciem.
Pozostałe wybory: TPN RGB 2018, NMT, NMPT oraz sam OSM. Regulacja krycia
podkładu i atrybucja są dostępne. NMT/NMPT są obrazami, nie źródłem
odczytu wysokości.

TPN: `https://tpn.obliview.com/Data/{rgb_2020|rgb_2018|NMT|nmpt}/{z}/{x}/{y}.jpg`,
źródłowe XYZ EPSG:3857, poziomy 15–20. Widok pozostaje EPSG:2180.
Używamy sprawdzonego `ol/source/XYZ`/TileImage/Canvas2D bez
`crossOrigin: 'anonymous'`. Nie odczytujemy pikseli i nie eksportujemy
płótna TPN. Nie zastępujemy tego źródła DataTile/WebGL.

OSM pozostaje pod TPN. Brak pojedynczego kafla odsłania OSM lokalnie,
bez przełączania całej mapy. Komunikat mówi o niewczytanej części podkładu,
nie zgaduje przyczyny (`404`, sieć, blokada przeglądarki). Po ograniczonej
liczbie prób pozostają OSM i „Spróbuj ponownie” dla bieżącego widoku.
Powrót nie zmienia wyboru podkładu, skali ani warstw. Zdarzenia poprzedniego
źródła nie zmieniają stanu nowego. Nie pobieramy kafli spoza widoku w celu
monitorowania usługi. OSM zgodnie z polityką dostawcy, bez masowego prefetchu.

## Publikacja i rollback

Po osobnej zgodzie na pierwszą publikację i jednorazowej konfiguracji
Pages, **Run workflow** wykonuje cały proces bez parametrów wersji:
Latest wszystkich źródeł → zapis przypięć → pobranie i walidacja → dane,
testy i build → archiwum gotowej paczki → publikacja. Każdy nowy klik
ponownie odczytuje wszystkie Latest; nowa wersja jednego źródła wystarcza.
Zmiany aplikacji i profilu przetwarzania też należą do tożsamości paczki.
Zwykły późniejszy deploy nie wymaga drugiego ręcznego etapu zatwierdzania.

Błąd pobierania, sumy, schematu, przetwarzania, testów lub buildu blokuje
job publikacji i zachowuje poprzednią stronę. Pobieranie może ograniczenie
ponawiać ten sam zasób po błędach sieci, `429` lub `5xx`; respektuje
`Retry-After`. Nie zmienia wersji i nie pomija wadliwego pliku.

### Przypięcia i ponowienia

- Pierwsze wybory zostają zapisane **przed pobieraniem** w niezmiennym
  artefakcie `inputs-<run_id>`; retencja **90 dni**, z odczytem potwierdzającym.
- `Re-run all jobs`, `Re-run failed jobs` i pojedynczy job korzystają
  z tych samych przypięć. **Re-run nigdy nie odczytuje ponownie Latest.**
  Brak manifestu zatrzymuje ponowienie z „Uruchom nowe Run workflow”.
- Gotowa zarchiwizowana paczka danego runu jest ponownie używana po
  kontroli sum, bez nadpisania pod tym samym ID. Jeśli build jej nie
  ukończył, można ponowić go z przypiętych wejść. Brak assetu lub zmiana
  sumy to błąd, bez zamiennika dobieranego po nazwie.
- Manifest wejść i manifest wyniku są oddzielne. Paczka przechowuje oba:
  repozytoria, wydania/tagi/commity/asset ID i URL, daty, oczekiwane
  i rzeczywiste SHA-256, commit aplikacji, wersje narzędzi, parametry
  przekształceń i raport techniczny. Wyników nie dopisujemy do przypięć.

### Gotowe paczki i retencja

Gotowe paczki z manifestami są assetami technicznych wydań `pages-<run_id>`
repozytorium mapy, bez oznaczenia Latest produktu i bez ciężkich plików
w historii Git. Artefakty Actions są transportem, nie archiwum rollbacku.

- Paczka bieżąca jest zachowana przez cały czas używania.
- Paczka zastąpiona jest dostępna co najmniej **15 dni od zastąpienia**,
  nie od pierwotnego buildu. `retention-days: 15` przy buildzie nie wystarcza.
- Rollback używa gotowej paczki i manifestów, bez Latest i ponownego buildu.
  Przywrócona paczka staje się bieżąca; po ponownym zastąpieniu otrzymuje
  nowe pełne 15 dni. Identyczna bieżąca paczka nie rozpoczyna retencji.
- Mały plik ewidencji na technicznej gałęzi zawiera bieżącą paczkę, daty
  zastąpienia, ostatnią operację i ewentualne `pending`. Warunkowy zapis
  wymaga poprzedniego SHA; konflikt zatrzymuje operację.
- Sprzątanie może działać po ręcznym deployu/rollbacku, bez harmonogramu.
  Chroni bieżącą i niejednoznaczne paczki; błąd odczytu ewidencji blokuje
  kasowanie. Nie gwarantujemy odtworzenia po upływie okna ani bezterminowego
  archiwum surowych wejść.

### Szeregowanie i przerwania

Finalne joby publikacji, rollbacku i sprzątania używają wspólnej grupy
`pages-production`, `cancel-in-progress: false`, `queue: max`.
Buildy mogą działać równolegle. Pod blokadą porównujemy oryginalne
`created_at` operacji z ostatnią ukończoną publikacją/rollbackiem.
Starszy run zostaje jawnie pominięty bez deployu; `run_id` i `run_number`
nie zastępują czasu. Równy czas i różne ID oznaczają zatrzymanie z powodem.
Rollback ma nowy czas operacji mimo starej paczki, więc dawny build go
nie nadpisze.

Sekwencja: sprawdzenie kolejności i archiwów → zapis `pending` chroniącego
obie paczki → oficjalne `actions/upload-pages-artifact` i `actions/deploy-pages`
→ potwierdzenie sukcesu → ewidencja zastąpienia → test publicznego adresu
i sprzątanie. Wykorzystujemy działający transport z próby GitHub;
nie budujemy własnego TAR dla Pages. Transport można odtworzyć z tej samej
paczki dla kolejnego `run_attempt`.

Deploy i zapis ewidencji nie są jedną transakcją. Przerwanie pozostawia
obie paczki chronione. Znany sukces konkretnego kroku deployu wraz ze
zgodnym publicznym identyfikatorem paczki pozwala uzgodnić ewidencję.
Nieznany lub sprzeczny wynik zatrzymuje kolejne publikacje i kasowanie
do **ręcznego rozpoznania**. Timeout nie oznacza nieudanego deployu;
nie ponawiamy POST w ciemno. Nie rozbudowujemy odzysku poza sprawdzony
mechanizm. Błąd testu publicznego adresu po potwierdzonym deployu jest
raportowany, ale nie powoduje automatycznego rollbacku.

Build raportuje sumę plików całej strony i blokuje publikację powyżej
**1 GB**. Transport, pliki strony i transfer widoku są różnymi wielkościami.
Nie ograniczamy po cichu katalogu lub rozdzielczości, aby zmieścić paczkę.
TPN/OSM nie należą do migawki; rollback nie cofa ich odpowiedzi.

## Kryteria odbioru

1. **Całość danych:** świeży klon pobiera przypięte źródła bez sąsiednich
   repozytoriów; raport zawiera rzeczywiste liczby obiektów, pomiarów,
   modeli i planów. Dane nie są ograniczone do przykładów. Integralność,
   nieobsługiwany schemat, brak składowej i wadliwy Best zatrzymują import.
2. **Geometria:** widok naprawdę EPSG:2180; testy osi, punktu kontrolnego,
   Z i pełnej transformacji rastra, w tym obrotu i pół piksela. Plan nie
   zmienia położenia po zmianie migawki GPS.
3. **Użyteczność:** wyszukiwanie bez znaków PL, wybór z mapy i listy,
   szczegóły i odrzucone w historii, przełączniki, poziome różnice,
   jawne relacje oraz braki. Wszystkie etykiety Best pozostają widoczne.
4. **Plany:** całość Miętusiej jako podgląd, szczegół i drobne napisy po
   zbliżeniu, obrót źródła, wariant PZA, nakładanie kilku planów, kolejność,
   krycie, wyłączenie i ponowienie błędu. Granice kafli przy DPR 1/2/3
   i niecałkowitym zoomie. „Pokaż cały plan” działa powyżej progu.
5. **Sieć i zasoby:** brak automatycznych obrazów przed progiem i spoza
   widoku; wyjątek dotyczy wybranego podglądu. Ograniczona równoległość,
   anulowanie niepotrzebnych pobrań i zwalnianie zasobów podczas nawigacji.
   Spóźniona odpowiedź nie zmienia aktualnego wyboru.
6. **Podkłady:** TPN rzeczywiście narysowane, OSM w lokalnej luce,
   błąd i ręczny powrót, wszystkie cztery warianty oraz sam OSM.
   Sam HTTP 200 lub poprawny fallback nie zalicza integracji TPN.
7. **Statyczna strona:** test zbudowanego artefaktu pod prefiksem
   `/jktz-mapa/`, bez proxy, serwera deweloperskiego i lokalnych ścieżek;
   jawne błędy, klawiatura, responsywność i brak błędów wykonania JS.
8. **Publikacja:** nowe Latest jednego źródła uwzględnione w nowym Run;
   Re-run zachowuje wejścia; błędny build nie publikuje; gotowa paczka
   rollbacku i retencja także po długim używaniu wersji. Sprawdzony model
   publikacji wykorzystujemy bez ponawiania całej rundy sond.
9. **Raport:** wyniki testów, gotowy podgląd, rozmiar strony, commit
   aplikacji i przypięcia wejść, ograniczenia i konkretna paczka do publikacji.
   Próby desktopowe (Chromium, Firefox, WebKit/Safari) i rzeczywiste telefony
   są raportowane osobno. Emulacja i desktop WebKit nie zaliczają iPhone'a.

Gotowość interfejsu oznacza działające wyszukiwanie, przesuwanie i wybór;
gotowość widoku oznacza narysowane wymagane warstwy lub jawne błędy.
TPN/OSM i plany raportujemy osobno. Dawne propozycje 1 MB transferu,
3 s gotowości i p95 klatki 33 ms nie są obietnicami ani arbitralną bramką
odbioru. Pomiary mają podawać sprzęt, silnik, DPR, sieć i stan cache.
JS heap lub budżet obrazów nie są pomiarem pełnej pamięci procesu/GPU.
Test telefonu obejmuje też orientację, ukrycie/powrót karty i stabilność;
nieprzeprowadzone próby pozostają jawne.
