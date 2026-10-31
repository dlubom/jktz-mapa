# Kontynuacja JKTZ 2D — wykonalność publikacji i przygotowanie implementacji

Pracuj w `/Users/dariuszlubomski/proj/jktz-mapa`.
Repozytorium: `https://github.com/dlubom/jktz-mapa`.
Sprawdź aktualne Git, PR i Pages; zachowaj zastane zmiany. Nie polegaj
na historii poprzedniego czatu ani na niezmienności zapisanych wersji.

Najpierw przeczytaj obowiązujące AGENTS.md, jeśli istnieją, oraz:

- `doc/PAGES_MAP_SPEC.md` — wymagania, rekomendacje i granice zakresu;
- `doc/PAGES_PUBLICATION_RESEARCH.md` — konkretna luka odzyskiwania deployu;
- `doc/PAGES_BROWSER_PROBE.md` — wykonane próby lokalne i publiczne;
- `doc/PAGES_INPUTS_RASTERS_PROBE.md` — źródła, sumy i cały katalog rastrów.

Starsze raporty wydajności/QGIS czytaj tylko dla potrzebnego kontekstu.

**Etap zakończony 2026-10-31:** wykonano próbę lokalną, a po osobnej zgodzie
użytkownika również ograniczoną próbę GitHub i przywrócenie sondy.
Przed kontynuacją przeczytaj również [wyniki próby](doc/PAGES_PUBLICATION_PROBE.md),
[aktualne ustalenia API](doc/PAGES_PUBLICATION_API_CHECK.md) oraz
[raport rzeczywistej próby GitHub](doc/PAGES_PUBLICATION_GITHUB_TRIAL.md).
[Procedura](doc/probes/publication/GITHUB_TRIAL.md) jest zapisem zatwierdzonej
próby, nie poleceniem ponownej inicjalizacji. Workflow jest zainstalowany,
lecz wyłączony w Actions. Release i gałąź ewidencji zostały zachowane.
Ponowne wykonanie sondy lokalnej jest dozwolone. Kolejna zmiana publiczna
i pełna aplikacja wymagają osobnego uzgodnienia.

Stan przekazania: publiczna sonda TPN działa pod
`https://dlubom.github.io/jktz-mapa/`, z osobnej gałęzi `gh-pages`.
Jej commit to `12a6783bc09eda112f9f187f9df5825264bbf183`. Pierwotna
publikacja `41183308660` i końcowe przywrócenie paczki `41187324619`
zakończyły się sukcesem. To odrzucalna sonda, nie aplikacja
ani docelowy workflow danych. Chromium i desktopowy WebKit potwierdziły
TPN w rzeczywistym EPSG:2180 bez proxy. Firefox nie wystartował w środowisku
testowym; natywne Safari, iPhone 14 Pro i rzeczywisty Android nadal czekają
na test. Nie zakładaj, że użytkownik już wykonał test telefonu.

Pełny wariant podglądów i kafli WebP512 dla 814 planów zmierzono:
275 282 006 B, 35 845 plików. To subtotal rastrów, nie gotowej strony
ani pamięci procesu. Sumy archiwów i przypięte metadane sprawdzono;
skrypty w `doc/probes/` są sondami, nie gotowymi importerami.

**Potwierdzony wynik:** lokalnie 13/13 scenariuszy; na GitHub A→B→odzysk→A,
dwie zachowane operacje w kolejce i ich blokada przez `pending`, bezczynny
drugi odzysk, pominięty stary Re-run B oraz przywrócenie `original`.
Odzysk potwierdzono po normalnym anulowaniu osobnego kroku oczekiwania
**po zakończonym sukcesem deployu**. Nie dowodzi to odzysku po twardym
zabiciu runnera ani utracie odpowiedzi wewnątrz POST. `unknown` nadal
chroni obie paczki i blokuje kolejną publikację oraz kasowanie.
Latest/przypięcia pełnych źródeł, długą retencję i cleanup sprawdzał tylko
model lokalny. Nie zaliczaj ich jako testu produkcyjnego workflow.

Możesz aktualizować dokumentację i wykonywać lokalne odrzucalne próby.
Dotychczasowe zgody publiczne objęły sondę TPN oraz zakończoną ograniczoną
próbę publikacji. Kolejna zmiana działających Pages, nowa próba oraz pełna
aplikacja/produkcyjny workflow wymagają osobnego uzgodnienia. Przygotuj
konkretny wynik przed pytaniem o zgodę. Sąsiednie repozytoria są tylko do odczytu; przyszły workflow
ma działać bez lokalnych checkoutów. README pozostaje bez nowych informacji
i linków do Pages; istniejące 3D pozostaje bez zmian.

Kontynuuj uzgodnienia ze specyfikacji, bez rozpoczynania wywiadu od początku
ani otwierania już podjętych decyzji. Nowy Run workflow sprawdza Latest
wszystkich trzech źródeł; Re-run zachowuje pierwotne wejścia. Bieżąca paczka
jest chroniona przez cały czas używania, zastąpiona przez 15 dni. Zachowaj
pozostałe decyzje użytkownika i odróżniaj je od rekomendacji technicznych.

Stosuj skille Matta Pococka proporcjonalnie: `mattpocock-skills:research`
dla konkretnych luk w dowodach, `mattpocock-skills:grilling` dla rzeczywistych
decyzji (jedno pytanie z rekomendacją), `mattpocock-skills:codebase-design`
dla granic modułów, `mattpocock-skills:prototype` tylko gdy pomaga zbadać
interfejs/model stanów. Fakty sprawdzaj sam; rutynowe wybory uzasadniaj jako
swoje rekomendacje. Po uzgodnieniu implementacji ustal granice testów,
stosuj `mattpocock-skills:tdd` dla istotnych zachowań
i `mattpocock-skills:code-review` do zmian.

Ten etap zakończono raportem lokalnym i raportem GitHub z dowodami.
Przed następnym etapem uzgodnij jego konkretny zakres; nie rozpoczynaj
pełnej aplikacji na podstawie zgody na sondę. Nie zaliczaj brakującego testu przez
emulację, fallback ani brak zauważonej awarii. Poza publikacją pozostają
szwy/gutter, nakładanie planów, zwalnianie zasobów i pamięć rzeczywistych
telefonów; nie mieszaj tych luk z potwierdzonymi wynikami.
