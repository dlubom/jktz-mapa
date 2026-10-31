# Próba wejść i pełnego katalogu rastrów

Badanie lokalne: **2026-10-31**. To sonda techniczna przed implementacją,
bez aplikacji, publikacji Pages i zmian w repozytoriach źródłowych.
Skrypty oraz małe wyniki są w [probes/inputs-rasters](probes/inputs-rasters/).
Ciężkie materiały robocze: `/private/tmp/jktz-input-probe`.
Nie są zależnością przyszłego workflow ani świeżego klonu.

## Wynik i granice

Ponownie pobrano i zweryfikowano bieżące wydania trzech źródeł. Ich wersje
pozostały zgodne z profilem z 2026-10-30. Odczytano cały katalog 814 planów,
sprawdzono wszystkie 2442 sumy składowych i zgodność 814 plików `meta.yaml`
z przypiętym commitem oraz manifestem. Przygotowano wszystkie podglądy
512 px i zmierzono pełną piramidę kafli 512 px: duże plany do natywnego
m/px, małe kończą się na podglądzie bez zwiększania rozdzielczości.

**Rekomendacja: kontynuować wariant bezstratnego WebP z podglądami
i kaflami 512 px.** COG nie jest potrzebny do rozstrzygnięcia obecnego
kosztu publikacji rastrów. Nadal wymagałyby go osobne argumenty oraz test
prawdziwego COG na docelowym Pages.

Wyniki nie dowodzą działania całej mapy, czytelności wszystkich napisów,
braku szwów przy dowolnym DPR ani zmieszczenia całego procesu telefonu
w pamięci. Oddzielna [próba przeglądarki](PAGES_BROWSER_PROBE.md) obejmuje
lokalne przypadki DPR 1/3. Nie zbadano gotowej strony na Pages ani
rzeczywistych telefonów.
Niniejsze skrypty są odtwarzalną sondą konkretnych wydań, nie gotowymi
importerami produkcyjnymi.

## Bieżące Latest i przypięcie

Odczyt API: 2026-10-31 około **07:32 UTC**. Sprawdzono `draft=false`,
`prerelease=false`; wszystkie trzy wydania miały `immutable=false`.
Odczytano wskazanie Latest, a nie własne sortowanie wersji. Rozwiązano
obiekty annotated tagów do commitów; `target_commitish` nie służy za commit.
Źródła: [Latest JKTZ](https://api.github.com/repos/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/releases/latest),
[Latest GPS](https://api.github.com/repos/dlubom/gps-kataster-obiektow-tatr/releases/latest),
[Latest Georeferencera](https://api.github.com/repos/dlubom/Georeferencer/releases/latest),
[API Releases](https://docs.github.com/en/rest/releases/releases#get-the-latest-release),
[API tagów](https://docs.github.com/en/rest/git/tags#get-a-tag).

| Źródło | Release / ID | Commit |
| --- | --- | --- |
| JKTZ | `v1.4.12` / `426443343` | `3f865414d1dacaa15cd5477e567b0f852c43b32d` |
| GPS | `v1.3.2` / `423386015` | `13d734213328e5491c1a5c3171e2cb0fdcef705c` |
| Georeferencer | `v0.7.4` / `429377515` | `a47c390955db88d7bdbb4eada4a9315884e9ccbe` |

| Asset | Asset ID | Bajty |
| --- | --- | ---: |
| `JKTZ-v1.4.12.zip` | `684414283` | 22 002 141 |
| `katalog.sqlite.zip` | `674981453` | 535 497 |
| `metadata.json` | `674981456` | 270 |
| `geotiff-tatry-v0.7.4.zip` | `693073187` | 21 746 297 |

SHA-256 w tej samej kolejności, **zgodne z `assets[].digest` API**:

```text
4e2b30ead79ee520c3a9fca84786e3112801fe8d7723d527bc07d81698cbbc91
b93b6ecfbf51a306d603abdea25f91d017313fa9d6d57288a64291f09c70e4b6
e51abd42c25791ada468e9736078a2ad669b055ef06277fffd955f3722cf9821
52a7f5a9238e5f4a2836b61f09cfe403ef101bcc3378fd4a27642f13db62d93b
```

Pełny zapis tożsamości, łańcuchów tagów i oczekiwanych sum:
[source-lock.json](probes/inputs-rasters/source-lock.json).
Pobranie sprawdzono także przez API asset ID z `Accept: application/octet-stream`.
Sonda odtworzeniowa używa tego sposobu i porównuje hash przed atomowym
zastąpieniem lokalnego pliku. Zapisane oczekiwane sumy pozostają oddzielne
od rzeczywiście wyliczonych. Ten lock odtwarza badanie; **nowe Run workflow
produktu nadal ma ponownie sprawdzać Latest wszystkich trzech źródeł**.

## Potwierdzony profil formatów

| Obszar | Wynik odczytu całej próbki |
| --- | --- |
| JKTZ | 73 modele SHP, 12 116 obiektów wektorowych łącznie; komplet SHP/SHX/DBF/PRJ, PolyLineZ, EPSG:32634 |
| GPS | 1028 obiektów, 1019 jaskiń, 1934 pomiary, 1028 rekordów Best; `integrity_check=ok`, brak błędów `foreign_key_check` |
| Georeferencer | 2443 wpisy ZIP: manifest i 2442 składowe; każda suma zgodna z `release.files[]` |
| TIFF | 814 odczytanych plików; EPSG:2180, jeden kanał, NBITS=1, CCITT Group 4, bez overview |
| Geometria | Rozmiary i sześć współczynników GDAL każdego TIFF-a zgodne z `acceptance`; nie zastąpiono transformacji prostokątem |
| Metadane | 814/814 `meta.yaml` zgodne z SHA-256 w `plans[].inputs`; dodatkowo zgodne z blobami Git wybranego commitu |

JKTZ: pola DBF nie dostarczają `object_id`; źródłem jawnego powiązania
pozostaje `gps_fix(station, object_id)` z przypiętego
[OTWORY.SRV.j2](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/blob/3f865414d1dacaa15cd5477e567b0f852c43b32d/Poligony/OTWORY.SRV.j2).
Szablonu nie wykonywano. Komentarze `; {{ gps_fix(...) }}` nie są aktywnymi
powiązaniami. Nie oceniano tu kompletności relacji model–obiekt.

GPS: `metadata_schema_version=1`, `data_schema_version=1`, tekstowe
`schema_version="1"` w SQLite. Klucz pomiaru to `(object_id, id)`.
`attachments` ma rzeczywiste pola `kind`, `path`, `caption`; w tej próbce
jest puste, podobnie jak `relations`. Brak rekordów nie jest uszkodzeniem
schematu. Zachowano 2129 źródłowych `validation_flags`; nie przeprowadzono
nowego audytu merytorycznego. Kontrakt pól wynika z
[DDL wydania](https://github.com/dlubom/gps-kataster-obiektow-tatr/blob/13d734213328e5491c1a5c3171e2cb0fdcef705c/src/gps_kataster_obiektow_tatr/build_db.py).

Georeferencer: potwierdzono `schema_version=1`, `status=complete`,
`content_version=t10-content-v1`, `release.version=t11-v2` i model
`t06-local-similarity-v1`. Nazwy TIFF-ów nie zastępują
`release.files[].plan_id/archive_path`. Pochodzenie, orientacja i źródłowe
CRS pozostają danymi źródła. Liczebności w tabeli są wynikami próbki,
nie stałymi walidatora. Źródło:
[układ paczki](https://github.com/dlubom/Georeferencer/blob/a47c390955db88d7bdbb4eada4a9315884e9ccbe/pipeline/release_layout.py).

### Pobieranie uzupełnień bez lokalnego checkoutu

Sprawdzono odrębnie pobranie drzewa Git z dokładnego commitu i wyłącznie
wybranych plików `raw.githubusercontent.com/{commit}/{path}`:

- Georeferencer: **816 plików, 1 246 817 B** — 814 `meta.yaml` oraz dwa
  istniejące opcjonalne pliki `source.json` / `image-identity.json`.
- JKTZ: trzy pliki, 25 510 B — szablon otworów i dwa pliki źródłowe użyte
  do zbadania kontraktu. Produkcyjny importer nie musi pobierać kodu
  eksportera tylko po to, by go przeczytać ponownie.

Limit równoległości sondy wynosił sześć pobrań. Każdy pobrany plik
porównano z SHA-1 obiektu Git z przypiętego drzewa; `meta.yaml` dodatkowo
z oczekiwanym SHA-256 manifestu. SHA-1 obiektu Git oblicza się wraz
z nagłówkiem `blob {długość}\0`; nie jest SHA-256 treści.
Brak/truncation drzewa zatrzymuje tę sondę.

Kontrolnie pobrany pełny tarball Georeferencera miał **629 043 823 B**,
JKTZ **111 045 069 B**. Nie jest to zalecana droga po same metadane.
Odtworzenie badania nie pobiera tych tarballi. Obliczono ich własne hashe,
ale nie traktowano ich jako porównania z opublikowanym digestem assetu.

### Próby błędów

Na kopiach rzeczywistych paczek przeprowadzono trzy pozytywne kontrole
i pięć negatywnych prób [sondy walidacyjnej](probes/inputs-rasters/negative_probe.py):

| Kontrolowana zmiana | Wynik sondy |
| --- | --- |
| Brak oczekiwanego digestu API | `UNSUPPORTED_INTEGRITY_CONTRACT` |
| Zmienione pobrane bajty | `ASSET_HASH_MISMATCH` |
| Zmieniona składowa w poprawnym ZIP-ie | `COMPONENT_HASH_MISMATCH` |
| Nieobsługiwane `schema_version=999` | `UNSUPPORTED_GEO_SCHEMA` |
| Usunięty SHX jednego modelu | `MISSING_SHP_COMPONENT` |

Wszystkie pięć zmian zostało odrzuconych zgodnie z oczekiwaniem. Nie jest
to pełna kampania bezpieczeństwa ZIP ani dowód działania przyszłych
importerów. Sonda nie testowała m.in. bomb dekompresyjnych, limitów całego
downloadu, wszystkich zduplikowanych kluczy JSON/YAML, przerwań GitHub,
ponowień workflow ani wyczerpania pamięci.

## Wszystkie rastry: piksele i wygenerowane warianty

Oryginały: 23 457 928 B TIFF-ów, **5 494 610 208 pikseli**.
`width × height × 4` daje **20,47 GiB** dla jednoczesnego RGBA katalogu.
To rachunek reprezentacji, nie pomiar RSS. 39 planów przekracza 100 MiB
takiego bufora. Największa Miętusia `001197` ma 28 660 × 16 266 px,
co odpowiada 1778,35 MiB RGBA przy TIFF-ie 1 314 417 B.

Warianty powstały przez GDAL 3.13.3 / Python 3.14.8 / NumPy 2.5.3
na macOS 27.0.1 arm64. Użyto pełnej transformacji wejściowej i north-up
EPSG:2180, interpolacji bilinear, mapowania 1-bitowego 0/1 na 0/255,
białego tła źródła i alfa poza źródłem. Każdy plan ma własną siatkę;
rozdzielczości piramidy to natywne m/px, następnie 2×, 4× itd., aż
pozostaje podgląd ≤512 px. To konkretna sonda reprezentacji, nie wybór
globalnej siatki XYZ dla produktu.

WebP: `LOSSLESS=YES`, `METHOD=4`; brak JPEG i stratnego WebP. Bezstratność
dotyczy wyniku resamplingu, a nie niezmienionych pikseli skanu.
Kafle brzegowe przycięto; nie dodawano gutterów i nie pomijano pustych
prostokątnych komórek. Zapisano wszystkie podglądy i kafle pięciu próbek;
pozostałe kafle kodowano, mierzono i zwalniano w `/vsimem/`.
Źródła metod: [transformacja GDAL](https://gdal.org/en/stable/tutorials/geotransforms_tut.html),
[WebP GDAL](https://gdal.org/en/stable/drivers/raster/webp.html).

| Zmierzony wariant, cały katalog 814 planów | Pliki | Piksele | Bajty plików |
| --- | ---: | ---: | ---: |
| Podglądy ≤512 px | 814 | 164 926 697 | 21 086 822 |
| Piramida kafli 512 px | 35 031 | 7 777 014 315 | 254 195 184 |
| **Razem** | **35 845** | **7 941 941 012** | **275 282 006** |

To **275,28 MB / 262,53 MiB**, zmierzone przez faktyczne kodowanie
wszystkich wariantów. Nie jest to ekstrapolacja kilku próbek. Subtotal
rastrów zajmuje około 27,5% z 1 GB; pozostawia znaczący margines, ale
nie zastępuje bramki rozmiaru całej strony.

Czasy są sumami ukończonych operacji lokalnych: podglądy 36,98 s,
piramida 407,94 s. Piramidę wznowiono po przerwaniu, sprawdzając pełny,
niepowielony zbiór 814 planów; nie jest to pomiar nieprzerwanego workflow
ani benchmark CI. Przed końcowym podsumowaniem ponownie porównano
hash archiwum z przypiętym digestem. W podglądach sprawdzono także,
że zaokrąglenie wymiarów nie zwiększa rozdzielczości ponad natywne m/px.
Zapis liczb i prób: [results.json](probes/inputs-rasters/results.json).

Nie należy wczytywać wszystkich podglądów z góry: ich jednoczesne RGBA
to **629,15 MiB**. Pojedynczy pełny kafel 512² px to 1 MiB RGBA,
256² to 0,25 MiB. Budżet 64 MiB obrazów nie oznacza 64 MiB procesu;
pozostają podkłady, wektory, etykiety, canvas, cache przeglądarki i GPU.

### 256 kontra 512 i PNG kontra WebP

Cała piramida Miętusiej, identyczne poziomy i 638 672 588 px:

| Wariant | Kafle | Bajty |
| --- | ---: | ---: |
| WebP 512 | 2565 | 8 278 670 |
| WebP 256 | 9906 | 8 453 222 |

256 px oznacza tu 3,86 razy więcej plików i o 2,1% więcej bajtów.
Nie dowodzi to czasu transferu telefonu lub przewagi 512 px w każdym
widoku. Dokładny geometryczny count całego katalogu 256 px wynosiłby
128 844 kafle; ich całkowitej kompresji nie zmierzono.

Na centralnych fragmentach 1024 × 1024 px sześciu planów, przy natywnej
rozdzielczości, WebP lossless miał **2,4–4,2 razy mniej bajtów** niż PNG
z `ZLEVEL=6`. Po odczycie porównano maskę alfa i wszystkie RGB tam,
gdzie alfa jest niezerowa: identyczne. RGB całkiem przezroczystych pikseli
nie jest miarą widocznej jakości. Niektóre WebP w całości nieprzezroczyste
poprawnie pomijają kanał alfa w pliku.

Próbki obejmują Miętusią, Piwnicę Miętusią PZA, Kokonową, Juhaską,
Komorę w Okręcie oraz Niedźwiedzią Niżnią (`001189`, obrót −90,68°).
To szersza próba kodowania i rotacji, nadal nie odbiór całego katalogu.
Miętusia: podgląd 512 ma 19 044 B, 1024 ma 53 570 B.
PZA: odpowiednio 32 256 B i 110 318 B. Podglądy 1024 wykonano tylko
dla tych sześciu planów; nie doliczono hipotetycznego wariantu 1024
całego katalogu do zmierzonego rozmiaru.

## Co pozostało do sprawdzenia

- Wykonano już [lokalną próbę OpenLayers](PAGES_BROWSER_PROBE.md):
  20/20 przypadków podglądów/kafli przy DPR 1/3. Należy czytać jej
  konkretne scenariusze i wyniki oględzin łącznie z tą inwentaryzacją;
  nie oznacza to pełnego odbioru czytelności katalogu.
- Wyświetlenie granic kafli przy niecałkowitym zoomie i DPR 1/2/3,
  obrót źródeł, krycie 75%, drobne napisy oraz białe tło na podkładzie.
  Brak guttera jest jawną granicą tej próby. Jeden piksel guttera przy
  512 px dodałby **55 925 254 px, około 0,72%** liczby pikseli piramidy;
  jest to wyliczenie geometrii, nie zmierzony przyrost skompresowanych bajtów.
- Dobór poziomu do CSS m/px i DPR oraz zachowanie „Pokaż cały plan”.
  Podgląd 512 px daje całość, ale nie obiecuje drobnego tekstu na DPR 3.
- Pobieranie/anulowanie/cache w OpenLayers w gęstych widokach, liczba
  żądań, p95 klatki i zimny start. Liczba kafli całego katalogu nie jest
  liczbą żądań jednego użytkownika.
- Pamięć całego procesu oraz stabilność na rzeczywistych iPhone/Safari
  i Android/Chrome. Ani desktopowa emulacja DPR, ani JS heap tego nie zamyka.
- Sumaryczny rozmiar finalnej strony z wektorami, historią, indeksami,
  aplikacją i metadanymi oraz rzeczywiste wdrożenie Pages. Zmierzony
  subtotal rastrów nie jest rozmiarem gotowej strony ani transportowego TAR.

## Odtworzenie na świeżym klonie

Potrzebne: `gh` z prawem odczytu publicznych API, `curl`, Python z GDAL
i NumPy oraz sterownikami WebP/PNG. Nie potrzeba sąsiednich repozytoriów,
lokalnego QGIS ani wcześniejszej paczki. Skrypty domyślnie zapisują ciężkie
pliki wyłącznie do `/private/tmp/jktz-input-probe`; można zmienić `--root`.

```sh
python3 doc/probes/inputs-rasters/fetch_inputs.py
python3 doc/probes/inputs-rasters/inspect_inputs.py
python3 doc/probes/inputs-rasters/negative_probe.py
python3 doc/probes/inputs-rasters/build_rasters.py --mode preview
python3 doc/probes/inputs-rasters/build_rasters.py --mode pyramid
python3 doc/probes/inputs-rasters/build_rasters.py --mode pyramid --tile 256 --limit 1
python3 doc/probes/inputs-rasters/compare_formats.py
```

W tej sesji interpreter z GDAL był pod `/opt/homebrew/bin/python3`.
Zapisane wersje opisują pomiar, nie zastępują przyszłego przypięcia
środowiska produkcyjnego. Uruchamiać komendy kolejno. Skrypt piramidy
umożliwia kontrolowane `--resume` w tym samym scratchu; to mechanizm
sondy, nie projekt Re-run GitHub Actions. Pliki JSON z pełnymi wynikami
pozostają w scratchu; zwięzły zapis wyników jest dołączony do dokumentacji.
