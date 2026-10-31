# Pierwsza mapa — odbiór 2026-10-31

Implementacja na gałęzi `feat/complete-map`. Publiczna sonda Pages nie została
zastąpiona. README, przeglądarka 3D i repozytoria źródłowe pozostają bez zmian.

## Dane i build

Świeży resolver wybrał JKTZ `v1.4.12`, GPS `v1.3.2` i Georeferencer
`v0.7.4`. Pobranie nie korzystało z sąsiednich checkoutów. Lock zawiera
release/asset ID, rozwiązane commity, oczekiwane sumy i źródłowe metadane.

| Zawartość | Wynik |
| --- | ---: |
| Obiekty / rekordy jaskiń | 1028 / 1019 |
| Pomiary / Best | 1934 / 1028 |
| Modele JKTZ / obiekty liniowe | 73 / 12 116 |
| Jawne relacje JKTZ | 82 |
| Plany / kafle szczegółów | 814 / 35 031 |
| Pliki danych / rozmiar | 39 602 / 301 382 969 B |

Sprawdzono wszystkie indeksowane ścieżki, wymiary 814 podglądów,
kafle każdego poziomu (514×514, komórka 512 plus gutter), zachowanie Z
wszystkich 24 232 wierzchołków JKTZ. Dwa rekordy jaskiń bez przypisanych
obiektów pozostają wyszukiwalne. `sourceCaveId` ma wartość tylko tam,
gdzie źródło podaje ją jawnie. Nie korygowano danych źródłowych.

Lokalny pełny build rastrów: 487,03 s, następnie odświeżenie metadanych
po review. Runtime: Python 3.14.8, GDAL 3.13.3, PROJ 9.9.0, NumPy 2.5.3,
PyYAML 6.0.3. CI zapisuje własne wersje i może wytworzyć inne bajty
resamplingu; rollback używa gotowej paczki.

## Sprawdzenia

- Python: 19 testów importerów i publikacji. JS: 7 testów wyszukiwania,
  osi, zakresu auto-planów, anulowania, ponawiania i limitu cache.
- TypeScript oraz statyczny build Vite przechodzą. Testy przeglądarek
  podają `dist/` pod prefiksem `/jktz-mapa/`, bez proxy aplikacji.
- Chromium i WebKit: komputer 1440×960/DPR1 oraz układ mobilny
  393×852/DPR3. Wyszukiwanie bez znaków PL, historia, domyślne warstwy,
  pozostałe/odrzucone/różnice, cały plan i szczegóły po przybliżeniu,
  krycie, kolejność, ukrycie, pochodzenie i jaskinia bez obiektu.
- Osobny live test na localhost: każdy z czterech podkładów TPN
  wyrenderowany w Chromium i WebKit (16/16 kafli w badanym widoku).
  OSM 28/28; awaria TPN po jednym autoretry: 32 błędy, OSM i komunikat;
  ręczne ponowienie: 16/16, TPN wraca i komunikat znika. Obrazy obejrzano,
  nie poprzestano na kodach HTTP. WebKit test awarii wymagał świeżego
  kontekstu, ponieważ rozgrzany cache nie wymusił żądanej awarii.
- Niezależne review objęło pipeline, publikację i interfejs. Wykryte
  utraty relacji/rekordów oraz problemy z mobile, kolejnością planów,
  podglądem i spóźnionymi odpowiedziami zostały poprawione.

Lokalne dowody: `.build/data-acceptance.json`, `public/data/build-report.json`,
`output/playwright/results.json`, `output/playwright/*.png`,
`output/live-basemap/review-summary.json` i zrzuty live. CI zachowuje
paczkę oraz dowody przeglądarki jako artefakty przebiegu.

## Pozostały odbiór i publikacja

- Fizyczne iPhone 14 Pro/Safari oraz Android/Chrome, natywne Safari,
  dłuższe używanie i pełna pamięć procesu/GPU urządzeń. DPR3 nie zastępuje
  telefonu, a limit bitmap nie jest limitem całej pamięci przeglądarki.
- Lokalny Firefox nie uruchomił sesji (błąd sandbox/framebuffer macOS
  i timeout startu). CI uruchamia ten sam scenariusz na Linuksie.
- Finalny pełny workflow i odczyt publicznej aplikacji dopiero po zgodzie.
  Przygotowane mechanizmy publikacji bazują na zakończonej próbie GitHub;
  ten odbiór nie jest kolejną próbą przerwania publicznego deployu.

Do zatwierdzenia: scalenie sprawdzonego PR, przełączenie wyłącznie
`jktz-mapa` z sondy na workflow Pages i pierwszy Run workflow. Nowy Run
ponownie sprawdzi Latest trzech źródeł. Obecna sonda ma zachowaną paczkę
rollbacku. Instrukcje i retencja: [IMPLEMENTATION.md](IMPLEMENTATION.md).
