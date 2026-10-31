# Lokalna próba publikacji i kandydat próby GitHub

Data: 2026-10-31. Etap: odrzucalna sonda mechanizmu publikacji, przed
implementacją aplikacji. Zdalne działania w tym etapie są tylko odczytami.
Nie włączono workflow ani nie zmieniono działających Pages.

## Punkt wyjścia sprawdzony na żywo

- Lokalny `main` był czysty, HEAD i zdalny `main`:
  `a5f7b79b1ff84faf0f66ae03123a010873474eae`.
- Brak PR-ów (odczyt wszystkich stanów). Jedyny przebieg Actions to
  [41183308660](https://github.com/dlubom/jktz-mapa/actions/runs/41183308660),
  `completed/success`. To ID przebiegu Actions, nie ID wdrożenia Pages.
- Pages: `built`, `build_type=legacy`, źródło `gh-pages:/`, HTTPS włączone,
  brak własnej domeny. Gałąź `gh-pages` wskazuje
  `12a6783bc09eda112f9f187f9df5825264bbf183`.
- Środowisko `github-pages` dopuszcza wyłącznie gałąź `gh-pages`.
  Workflow uruchamiany z `main` potrzebuje osobno dopuszczonej reguły.
- Ponowny odczyt publicznego HTML, JS i CSS: wszystkie trzy SHA-256 zgodne
  z opublikowaną sondą; razem 389 250 B. To kontrola bajtów, nie nowy test
  renderowania, TPN ani telefonu.

Migawka z godziną odczytu, ustawieniami i sumami:
[remote-before.json](probes/publication/remote-before.json).
Przed dopuszczoną próbą należy ponownie sprawdzić te warunki; zmiana
`gh-pages`, publicznych bajtów lub konfiguracji zatrzymuje procedurę.

## Próba lokalna

Odtworzenie bez sieci i dodatkowych bibliotek:

```sh
python3 doc/probes/publication/local_probe.py
```

[Skrypt](probes/publication/local_probe.py) tworzy osobny katalog tymczasowy
dla każdego scenariusza, zapisuje atrapę API i ewidencję na dysku, a po
kontrolowanym przerwaniu otwiera je nowym klientem. Raport zapisuje
[local-results.json](probes/publication/local-results.json). Katalogi
tymczasowe są usuwane; źródła mapy nie są pobierane ani zmieniane.

| Scenariusz | Obserwacja lokalna |
| --- | --- |
| A działa 120 dni, potem A→B→A→B | Bieżące A nie wygasa. Pierwsze zastąpienie chroni A do dnia 135; ponowne do dnia 137. Usunięcie dopiero na granicy pełnych 15 dni. |
| Starszy build po rollbacku | Odrzucony bez POST. Równe czasy różnych operacji także blokują deploy; ponowienie zakończonej operacji nie publikuje drugi raz. |
| Nowy run / Re-run | Dwa nowe runy wykonują po trzy odczyty Latest. Re-run zachowuje przypięcia mimo zmiany jednego źródła; brak, uszkodzenie i niekompletność kończą się odmową bez odczytu Latest. |
| Przerwanie zapisu przypięć | Przed trwałym zapisem: potrzebne nowe Run workflow. Po utracie odpowiedzi kompletnego uploadu: odczyt istniejących przypięć. |
| Przerwanie wewnątrz deployu | Strona w atrapie zmienia się na B, ale bez dowodu sukcesu dokładnego kroku pozostaje `pending`; oba archiwa są zachowane, deploy i sprzątanie zablokowane także po ponownym otwarciu stanu. |
| Przerwanie po udanym kroku | Sukces zapisanej próby/joba/kroku plus zgodna strona pozwalają zakończyć ewidencję bez drugiego POST. Potwierdzenie w dniu 10 chroni A do dnia 25. |
| Niewystarczające dowody | Inna próba, run, job, krok, cancel, brak/stara strona lub zły hash nie rozwiązują `pending`. |
| Konflikt CAS / utrata odpowiedzi | Po każdej niejednoznacznej odpowiedzi następuje odczyt. Zgodny zapis jest rozpoznawany; inny stan zatrzymuje operację bez ślepego powtórzenia. |
| Zmieniona paczka / blokada | Zmienione bajty odrzucone; konkurencyjny deploy i cleanup nie wchodzą podczas lokalnej blokady. |
| Brak lub uszkodzenie ewidencji | Sprzątanie zatrzymuje się bez usunięcia jakiejkolwiek paczki, także już kwalifikującej się do usunięcia. |
| Brak archiwum / publikacja tej samej paczki | Brak bieżącej lub docelowej paczki blokuje POST i zapis `pending`. A→A nie rozpoczyna retencji A. |
| Kandydat rollbacku po upływie retencji | Jawnie zarejestrowane wygasłe B nie jest usuwane i może zostać przywrócone. Rejestr kandydatów jest tu fixture, nie odczytem kolejki GitHub. |
| JSON o niepoprawnym schemacie | `pending=[]`, `pending={}` i inne wadliwe typy blokują publish/cleanup; działające B pozostaje dostępne. |

Wynik powtórnego uruchomienia: **13/13 scenariuszy zaliczonych**.
Powtórny odzysk bez `pending` jest bezczynny: bez drugiego POST, zmiany
bajtów ewidencji ani przesunięcia już ustalonego terminu ochrony.

Niezależny przegląd początkowej sondy wykrył brak ochrony oczekującego
kandydata oraz pomylenie wadliwego `pending=[]` z brakiem operacji.
Oba przypadki odtworzono i poprawiono w modelu. To uzasadnia sprawdzanie
schematu ewidencji przed interpretacją oraz jawną ochronę kandydatów;
sam poprawny JSON i wykluczenie `current` z kasowania nie wystarczają.

**Wniosek dla próby GitHub:** warto sprawdzić odzysk po ukończonym kroku
publikacji, używając oryginalnej próby Actions i odczytu strony.
Nie ma podstaw do automatycznego ponawiania deployu przy `unknown`.
Utrata odpowiedzi zapisu ewidencji nie powinna oznaczać ponownej publikacji.

## Konkretny kandydat GitHub — nieuruchomiony

[Procedura do zatwierdzenia](probes/publication/GITHUB_TRIAL.md),
[nieaktywny YAML](probes/publication/github-candidate.yml),
[skrypt operacji](probes/publication/github_probe.py),
[przygotowanie paczek](probes/publication/prepare_packages.py) i
[przypięte sumy](probes/publication/packages.json) stanowią komplet do
przeglądu. YAML jest w `doc/probes`, poza `.github/workflows`.

Minimalna próba używa obecnej sondy, bez buildu mapy i pobierania danych
trzech repozytoriów. Paczki A i B zachowują HTML, JS, CSS oraz `.nojekyll`
oryginału; dodają wyłącznie różniący je `publication-probe.json`.
Paczka `original` nie ma tego pliku. Każde gotowe archiwum TAR ma
399 360 B; wszystkie trzy razem 1 198 080 B. Nie jest to rozmiar aplikacji
ani artefaktu transportowego ZIP Actions.

Proponowana sekwencja: publikacja A → publikacja B → potwierdzenie sukcesu
dokładnego kroku i anulowanie w osobnym kroku oczekiwania przed ewidencją
→ osobny `recover` → rollback gotowej A → przywrócenie `original` → powrót
do obecnego źródła `gh-pages:/` w trybie `legacy` i końcowy odczyt strony.
Nie uznawać kontrolowanego błędu kroku za dowód anulowania runnera.

Próba potrzebuje jednego technicznego release z trzema archiwami, gałęzi
`pages-probe-state`, ręcznego workflow na `main`, czasowej reguły `main`
w środowisku `github-pages` oraz czasowej zmiany źródła Pages. Nie usuwa
archiwów. Gałąź `gh-pages` i jej dotychczasowa reguła pozostają zachowane.
Dokładne komendy, warunki zatrzymania i procedura przywrócenia są w
podlinkowanym dokumencie. Taki zakres wymaga osobnej zgody użytkownika.

To celowo węższa próba od przyszłego workflow produktu: przypięcia Latest,
zmianę źródeł, równoległe buildy oraz retencję testuje na razie model
lokalny. Żadnego z tych kontraktów nie zmieniamy na stałe przypięcia
małej sondy. Automatyczne sprzątanie nie jest częścią próby GitHub.

## Weryfikacja przygotowanego wyniku

- Powtórzona lokalna sonda: 13/13 scenariuszy.
- Niezależnie odtworzono wszystkie trzy archiwa; identyczne TAR-y i sumy
  wszystkich składowych, brak dodatkowych plików poza markerami A/B.
- [Kontrola kodu kandydata](probes/publication/candidate_check.py), uruchamiana
  przez `python3 doc/probes/publication/candidate_check.py`, sprawdza jego
  rzeczywiste funkcje przy podstawionym API: original→A→B→recover→A→original,
  utratę odpowiedzi CAS, bezczynny drugi odzysk oraz stare/równoczesne runy.
  Transport archiwów i publiczny odczyt w tej kontroli są atrapami.
- Niezależny przegląd wykrył również `last={}` omijające kontrolę starszego
  runu w kandydacie. Poprawiono walidację ewidencji i potwierdzono odmowę;
  przeglądy modelu, kodu oraz procedury nie pozostawiły istotnych uwag.
- Sprawdzono składnię Python i bloków poleceń procedury. `actionlint`
  **1.7.12** nie zna jeszcze pola `concurrency.queue`; bez wyjątków zgłasza
  dokładnie tę jedną diagnostykę. Po selektywnym pominięciu jej walidacja
  pozostałej części YAML przechodzi. `queue: max` potwierdzono osobno
  w aktualnej dokumentacji GitHub; akceptacja przez rzeczywiste Actions
  pozostaje częścią planowanej próby. Nie usunięto pola dla zielonego lint.
- [Końcowy odczyt zdalny](probes/publication/remote-after.json),
  **2026-10-31 08:35:49 UTC**, potwierdził niezmienione gałęzie, konfigurację
  Pages, reguły środowiska, listę PR-ów i przebiegów oraz trzy publiczne
  SHA-256. Repo zdalne i działająca sonda nie zostały zmienione.

## Granice dowodów

Lokalna atrapa API sprawdza model stanów i kontrolowane awarie zapisu.
Nie dowodzi semantyki kolejki Actions, trwałości wyników kroków po
przerwaniu runnera, propagacji CDN ani możliwości automatycznego odzysku
przerwania wewnątrz deployu. Wynik `unknown` pozostaje stanem wymagającym
rozpoznania; nie wolno zamienić go na „deploy nie nastąpił”.

Osobno nadal pozostają: natywne Safari, rzeczywisty iPhone 14 Pro oraz
Android/Chrome, pamięć telefonu, szwy/gutter, nakładanie planów i zwalnianie
zasobów. Ten etap nie zmienia ich statusu ani uzgodnionych decyzji mapy.
