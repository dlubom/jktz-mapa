# Testowanie zmian z PR

Każdy PR buduje pełną mapę i uruchamia testy danych oraz Chromium, Firefox i WebKit.
Zmiany `main` wymagają PR i zielonego testu `map`. Bezpośrednia zmiana `main`
wymaga wyraźnego polecenia użytkownika i czasowego odblokowania ochrony.

## Pobranie gotowej mapy

W PR otwórz **Checks → map → Details**. W podsumowaniu uruchomienia jest
**Pobierz kompletny ZIP**; ten sam plik znajduje się w **Artifacts** jako
`preview-<run_id>-<attempt>`. Pobieranie wymaga zalogowania do GitHub.
Paczka jest dostępna przez 15 dni od utworzenia.

Rozpakuj cały ZIP do nowego folderu. W tym folderze uruchom:

```sh
python3 serve.py
```

Na Windows z Python Launcher: `py -3 serve.py`. Potrzebny jest Python 3.9 lub
nowszy; Node, GDAL i QGIS nie są potrzebne. Otwórz adres wypisany przez skrypt,
zwykle `http://127.0.0.1:4173/`. Zatrzymanie: Ctrl+C. Zajęty port można zmienić:
`python3 serve.py --port 4174`.

ZIP zawiera gotową aplikację, pełne katalogi i wszystkie obrazy planów.
Podkłady TPN, PIG i OSM oraz odnośniki wymagają internetu. Otwarcie samego
`index.html` bez serwera HTTP nie wystarcza.

`preview.json` identyfikuje PR i head/base/merge SHA, `inputs.json` przypina
wydania źródeł, a `checksums.json` zawiera SHA-256 wszystkich pozostałych plików.
Wersję testową oznacza też widoczny pasek na mapie. ZIP z uruchomienia `push`
lub ręcznego CI może nie mieć numeru PR; ZIP z testu PR identyfikuje kandydata scalenia.

## Opublikowanie wybranego PR

1. Otwórz [Preview selected PR](https://github.com/dlubom/jktz-mapa-preview/actions/workflows/preview.yml).
2. Kliknij **Run workflow**, pozostaw gałąź `main` i wpisz numer otwartego PR
   w `dlubom/jktz-mapa`, którego bazą jest `main`.
3. Poczekaj na zielone etapy `resolve`, `build` i `publish`.
4. Otwórz **[stronę testową](https://dlubom.github.io/jktz-mapa-preview/)**.

Jeden adres pokazuje jeden wybrany PR. Kolejny udany Run zastępuje podgląd;
nieudany build lub test pozostawia poprzednią stronę. Numer PR i skrót commita
widać na mapie, pełną tożsamość pod `preview.json`. Po zmianie PR lub `main`
uruchom podgląd ponownie. Wdrożenie odrzuca PR zamknięty, konfliktowy lub zmieniony
od przypięcia kandydata. Ponowna kontrola odbywa się po wysłaniu paczki, tuż
przed wdrożeniem. Starszy wybór nie może nadpisać nowszego: jeżeli uruchomiono
nowszy Run, starszy Run i jego Re-run nie opublikują strony. Aby ponownie wybrać
wcześniejszy PR, użyj nowego **Run workflow**. W tym samym Run dostępny jest pełny ZIP.

Podgląd niezależnie buduje pełne dane, więc jego migawka źródeł może różnić się
od wcześniejszego ZIP z CI źródła. Porównuj `inputs.json`. Każdy Run/Re-run
rozpoznaje aktualny PR i Latest źródeł; powtarzanie identycznej paczki nie jest
kontraktem tego podglądu. Produkcyjny proces przypięć i rollbacku pozostaje osobny.

## Utrzymanie konfiguracji

Repozytorium podglądu zawiera tylko workflow, publikator i instrukcję. Nie trzyma
kopii wygenerowanych danych w Git. Wersje tych plików są w repozytorium aplikacji:

| Źródło | Repozytorium podglądu |
| --- | --- |
| `.github/preview-repository/preview.yml` | `.github/workflows/preview.yml` |
| `scripts/preview.py` | `scripts/preview.py` |
| `scripts/preview-server.py` | `scripts/preview-server.py` |

Zmiany publikatora przenoś osobnym PR do repozytorium podglądu. Kod wybranego PR
wykonuje się bez sekretów i z `contents: read`; publikacja ma osobny runner,
zaufany checkout, weryfikację paczki i uprawnienia Pages/OIDC. Nie wymaga PAT ani
kluczy wdrożeniowych. Środowisko `github-pages` dopuszcza wyłącznie `main`.
Podgląd nie wdraża aplikacji produkcyjnej i nie zmienia `pages-state`.
