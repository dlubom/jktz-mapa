# Prompt do dalszego dopracowania projektu

Użyj skilla `mattpocock-skills:grilling`, aby dopracować projekt mapy 2D
Jaskiniowego Katastru Tatr Zachodnich. Pracuj w katalogu:
`/Users/dariuszlubomski/proj/jktz-mapa`.

Najpierw przeczytaj:

- `doc/PAGES_MAP_SPEC.md` — uzgodnione wymagania, propozycje techniczne i kwestie otwarte;
- `doc/PAGES_MAP_PERFORMANCE.md` — wcześniejsze pomiary i ich ograniczenia;
- `doc/QGIS_WASM_RESEARCH.md` — analiza alternatyw i ograniczeń hostingu.

To etap projektowy. Możesz aktualizować te dokumenty w miarę ustaleń.
Repozytorium `https://github.com/dlubom/jktz-mapa` zostało utworzone
na osobne polecenie użytkownika, aby zapisać dokumentację w Git.
Nie implementuj aplikacji i nie publikuj strony; Pages pozostaje wyłączone.

Kontynuuj od kwestii otwartych w specyfikacji, zamiast powtarzać zakończony
wywiad. Uzgodnione są: osobne repo i Pages dla 2D; nienaruszone istniejące 3D;
jedno ręczne Run workflow, które przy każdym nowym kliknięciu ponownie
sprawdza GitHub Latest z trzech repozytoriów i wdraża dostępne nowsze
wydania (wystarczy zmiana jednego źródła); wybory są przypięte tylko
w obrębie danego runu i jego Re-run; tylko techniczna walidacja formatów
i struktury; OpenLayers;
ręczny rollback gotowej paczki przez 15 dni od zastąpienia; fallback TPN → OSM
z komunikatem; odbiór na rzeczywistych Android/Chrome i iPhone/Safari.
Pozostałe wymagania mapy, warstw i pochodzenia danych zachowaj ze specyfikacji.

Sprawdź fakty w dostępnych plikach i oficjalnych źródłach przed pytaniem.
Zadawaj po jednym najważniejszym pytaniu o rzeczywistą decyzję użytkownika,
z rekomendacją i konsekwencjami. Rutynowe wybory techniczne uzasadniaj sam.
Kwestionuj złożoność i obietnice bez dowodów; nie traktuj całej specyfikacji
ani proponowanych progów wydajności jako zatwierdzonych.

Skup się na wykonalności TPN w EPSG:2180 na czystym Pages, konkretnych
kontraktach release assets, kaflach/podglądach kontra COG, czytelności,
pełnej pamięci telefonu, rozmiarze publikacji oraz prostym przechowywaniu
paczek do rollbacku. Zaprojektuj obsługę błędów, ponowień i współbieżności
bez komplikowania zwykłego „kliknij i wdroż najnowsze”. Oddzielaj pomiary,
szacunki, cele i testy dopiero potrzebne. Brak dowodu pozostaw jawnym ryzykiem.

Repozytoria sąsiednie i wskazane w raportach lokalne dowody służą tylko
do odczytu; nie są zależnościami przyszłego workflow. Zachowaj zakaz nowych
informacji i linków do Pages w README.

Na końcu zaktualizuj dokumenty tak, aby rozstrzygnięcia były spójne,
otwarte ryzyka miały określony sposób weryfikacji, a kontrakt jednego
kliknięcia był jednoznaczny. Przedstaw pozostałe decyzje i kryteria gotowości
do implementacji. Nie rozpoczynaj implementacji w ramach tego zadania.
