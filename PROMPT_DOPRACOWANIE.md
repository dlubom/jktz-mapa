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

**Uzupełnienie etapu 2026-10-31:** lokalną próbę opisaną niżej wykonano.
Przed kontynuacją przeczytaj również [wyniki próby](doc/PAGES_PUBLICATION_PROBE.md),
[aktualne ustalenia API](doc/PAGES_PUBLICATION_API_CHECK.md) oraz
[konkretną próbę GitHub do zatwierdzenia](doc/probes/publication/GITHUB_TRIAL.md).
Jej YAML znajduje się poza `.github/workflows` i nie został uruchomiony.
Najbliższa decyzja dotyczy wyłącznie tej ograniczonej próby; brak zgody
nadal blokuje zmiany publiczne. Ponowne wykonanie sondy lokalnej jest
dozwolone. Poniższy opis zachowuje zakres i kryteria tego etapu.

Stan przekazania: publiczna sonda TPN działa pod
`https://dlubom.github.io/jktz-mapa/`, z osobnej gałęzi `gh-pages`.
Jej commit to `12a6783bc09eda112f9f187f9df5825264bbf183`, wdrożenie
`41183308660` zakończyło się sukcesem. To odrzucalna sonda, nie aplikacja
ani docelowy workflow danych. Chromium i desktopowy WebKit potwierdziły
TPN w rzeczywistym EPSG:2180 bez proxy. Firefox nie wystartował w środowisku
testowym; natywne Safari, iPhone 14 Pro i rzeczywisty Android nadal czekają
na test. Nie zakładaj, że użytkownik już wykonał test telefonu.

Pełny wariant podglądów i kafli WebP512 dla 814 planów zmierzono:
275 282 006 B, 35 845 plików. To subtotal rastrów, nie gotowej strony
ani pamięci procesu. Sumy archiwów i przypięte metadane sprawdzono;
skrypty w `doc/probes/` są sondami, nie gotowymi importerami.

**Najbliższy cel:** sprawdź prosty mechanizm publikacji, ponowień,
współbieżności i odzyskania przerwania między deployem a zapisem ewidencji.
Zacznij od konkretnej lokalnej próby stanów i kontrolowanych awarii:
A→B→A, starszy build po rollbacku, brak przypięć przy Re-run, wersja bieżąca
używana ponad 15 dni oraz wynik deployu `unknown`. Sprawdź proponowaną
ochronę obu paczek i zakaz usuwania przy niejednoznacznym stanie.
Atrapa API sprawdza logikę; nie dowodzi zachowania GitHub po przerwaniu runnera.
Następnie przygotuj minimalną, recenzowalną próbę na GitHub, z dokładnym
zakresem zmian i sposobem przywrócenia obecnej sondy. Nie kończ na ogólnym planie.

Możesz aktualizować dokumentację i wykonywać lokalne odrzucalne próby.
Dotychczasowa zgoda publiczna dotyczyła tylko sondy TPN. Zmiana działających
Pages, uruchomienie nowej próby publikacji oraz pełna aplikacja/produkcyjny
workflow wymagają osobnego uzgodnienia. Przygotuj konkretny wynik przed
pytaniem o zgodę. Sąsiednie repozytoria są tylko do odczytu; przyszły workflow
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

Zakończ etap wynikiem lokalnych prób, przygotowaną próbą GitHub i krótką
listą nadal brakujących dowodów. Nie zaliczaj brakującego testu przez
emulację, fallback ani brak zauważonej awarii. Poza publikacją pozostają
szwy/gutter, nakładanie planów, zwalnianie zasobów i pamięć rzeczywistych
telefonów; nie mieszaj tych luk z potwierdzonymi wynikami.
