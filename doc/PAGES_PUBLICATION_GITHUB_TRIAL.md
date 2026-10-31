# Próba publikacji na GitHub — wynik i dowody

Data: 2026-10-31. Użytkownik zatwierdził zakres
[przygotowanej próby](probes/publication/GITHUB_TRIAL.md): techniczny release,
gałąź ewidencji, ręczny workflow, czasową konfigurację Pages i przywrócenie
oryginalnej sondy. To nie zgoda na pełną aplikację.

**Wynik: zatwierdzona próba zakończona, oryginalne Pages przywrócone.**
Potwierdzono A→B→odzysk→A, kolejkę, blokadę przez `pending`, bezczynny drugi
odzysk i pominięcie starego Re-run. Odzysk dotyczy anulowania osobnego
kroku oczekiwania po ukończonym deployu; nie twardego zabicia runnera
ani przerwania wewnątrz POST. Dwie pierwsze próby A nie powiodły się;
oficjalne pakowanie transportu umożliwiło wykonanie całej sekwencji.

Trwałe [dowody JSON](probes/publication/github-results.json) zawierają
wybrane pola odpowiedzi Runs/Jobs API, migawki ewidencji i ich SHA,
kolejkę przed anulowaniem, odrzucenia, fragmenty logów oraz końcowe
odczyty konfiguracji i sum pobranych plików. Odczyt końcowy:
**2026-10-31 09:08:56 UTC**. Dalsze sekcje opisują przebieg i jego granice.

## Stan początkowy i przygotowanie

Ponownie sprawdzono `main=a5f7b79b1ff84faf0f66ae03123a010873474eae`, brak
PR-ów i ochrony main, Pages `legacy`, źródło `gh-pages:/` pod
`12a6783bc09eda112f9f187f9df5825264bbf183`. Trzy publiczne sumy zgodne,
marker próby nie istnieje. Lokalna sonda: 13/13; kontrola kandydata oraz
odtwarzalność trzech archiwów przeszły ponownie.

Zainstalowany commit: `846a806ba1e9936efea869f6336ac18c81e0b9f6`.
Workflow: `402595194`. Release techniczny `429817445`, utworzony
z `make_latest=false`, zachowuje gotowe paczki original/A/B. Wszystkie
trzy pobrano po asset ID i sprawdzono przed inicjalizacją ewidencji.
Gałąź `pages-probe-state` zaczyna od `current=original`, bez historii
zastąpienia i bez `pending`. Tymczasowa reguła main: `65006113`;
oryginalna reguła gh-pages: `65003853` pozostaje zachowana.

## Pierwsza publikacja A — końcowy błąd Pages

[Run 41185758641](https://github.com/dlubom/jktz-mapa/actions/runs/41185758641),
próba 1, job `124492241688`: zapis i odczyt `pending` przeszły, krok 6
`Publish Pages probe` zakończył się błędem. Przyszły krok był widoczny
w Jobs API przed deployem, więc ten warunek przygotowania potwierdzono.

Akcja przyjęła żądanie, po czym Pages zwróciło `deployment_failed`.
Odczyt `/pages/deployments/846a806ba1e9936efea869f6336ac18c81e0b9f6`
potwierdził ten sam status. To jedyne wysłane wdrożenie pod tym SHA.
Dokładny job/run jest zakończony, środowisko zgłasza failure; treść błędu
nie podaje przyczyny. Pobrany artefakt transportowy zawiera dokładnie
`artifact.tar` z bajtami A zgodnymi z release. Publiczne trzy pliki są
zgodne z oryginałem, marker nadal zwraca 404.

[Przypięty kod deploy-pages](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/deployment.js#L16)
odróżnia końcowy `deployment_failed` od `deployment_attempt_error`,
timeoutu i utraty statusu. Przy tym końcowym stanie kończy odpytywanie.
Sam status nie wyjaśnia, czy przyczyną była usługa, czy artefakt.

**Rozstrzygnięcie operatora:** po świeżym potwierdzeniu terminalnego
statusu, braku aktywnych przebiegów i zgodnego oryginału można uzgodnić
tę konkretną próbę jako odrzuconą. Zachować jej pełne `pending` i dowody
w ewidencji odrzuconych operacji, a warunkowym zapisem wyczyścić wyłącznie
to `pending`. `current`, `last` i retencja pozostają bez zmian. To ręczne
rozpoznanie końcowego błędu, nie automatyczny odzysk ani zaliczenie
scenariusza przerwania po sukcesie.

W dalszym rozpoznaniu znaleziono konkretną niezgodność: transportowy TAR
nie miał prefiksu `./` w nazwach wpisów. Wymóg celowej walidacji backendu
potwierdza [odpowiedź w repo akcji](https://github.com/actions/deploy-pages/issues/203#issuecomment-1652804586).
Poprzedni udany artefakt sondy miał ten prefiks; pierwszy A go nie miał.
Generyczny status sam w sobie nie ujawnia przyczyny, ale niezgodność
z wymaganym formatem jest potwierdzona. Zrezygnowano z ponowienia
niezmienionego transportu.

Minimalna poprawka dodaje `./` wyłącznie do nazw wpisów transportowego
TAR. Pliki, pozostałe metadane i archiwa w release pozostają bez zmian;
nie przebudowuje to strony ani nie wybiera nowych źródeł. Regresja
w `candidate_check.py` najpierw odtworzyła brak prefiksu, następnie przeszła
po poprawce. Kolejny commit pozwolił też odróżnić endpoint statusu Pages
od pierwszego nieudanego wdrożenia. Następna próba wykazała, że ta korekta
nie wystarczyła do udanej publikacji.

## Druga próba A — poprawiony prefiks nie wystarczył

[Run 41186232166](https://github.com/dlubom/jktz-mapa/actions/runs/41186232166),
commit `9d6bc4d27e4fc6cc05e089f0b2a0139ef49e2228`, job `124493604633`:
zapis `pending` przeszedł; krok deployu ponownie otrzymał terminalny
`deployment_failed`. Publiczny oryginał pozostał zgodny. Tę konkretną
operację rozpoznano i zapisano osobno tak samo jak pierwszą, bez zmiany
wersji i retencji. Obydwa dawne `pending` są w `rejected_operations`.

**Rozstrzygnięcie:** nie ma dowodu, że brak prefiksu był jedyną przyczyną.
Zamiast dodawać kolejne warianty własnej serializacji, następna próba
użyła całej oficjalnej akcji `upload-pages-artifact` v5.0.0, SHA
`fc324d3547104276b827a68afc52ff2a11cc49c9`. Runtime materializuje wyłącznie
zweryfikowany inwentarz plików, a akcja przygotowuje natywny TAR i upload.
`include-hidden-files=true` zachowuje `.nojekyll`. Zmiana obejmuje transport,
bez nowych paczek, źródeł, zmian strony lub reguł odzyskiwania.
To próba implementacji referencyjnej, nie twierdzenie o ustalonej przyczynie
drugiego błędu. Lokalna kontrola potwierdza identyczne pliki original/A/B.

## Sekwencja po przejściu na oficjalny transport

Wszystkie poniższe operacje wykonały ten sam kod
`5dbf3f8f7a7842b2fc2fde8cf42a3bb413173cf4`. Nie zmieniano assetów A/B/original.
To istotne: SHA workflow jest wspólne dla różnych paczek, dlatego odzysk
opiera się na dokładnym runie, próbie, jobie i kroku, a nie samym SHA.

| Operacja / run | Próba / job | Wynik |
| --- | --- | --- |
| [A](https://github.com/dlubom/jktz-mapa/actions/runs/41186555255) | 1 / `124494546306` | Sukces kroków 6 i 8, `current=A`; oryginał chroniony 15 dni od potwierdzenia. |
| [B](https://github.com/dlubom/jktz-mapa/actions/runs/41186621744/attempts/1) | 1 / `124494742113` | Krok 6 success, publiczne B potwierdzone; zwykłe anulowanie podczas kroku 7. Cały run/job cancelled, krok 7 cancelled, krok 8 skipped. |
| [Kolejka A1](https://github.com/dlubom/jktz-mapa/actions/runs/41186718473) | 1 / `124495266941` | Zachowana w kolejce; następnie oczekiwany failure na przygotowaniu: `pending/unknown`. Bez deployu. |
| [Kolejka A2](https://github.com/dlubom/jktz-mapa/actions/runs/41186723574) | 1 / `124495298623` | Zachowana równocześnie z A1; następnie ta sama blokada bez deployu. |
| [Odzysk B](https://github.com/dlubom/jktz-mapa/actions/runs/41186880269) | 1 / `124495505745` | Sukces bez deployu. `current=B`, `pending=null`, `last` wskazuje pierwotne B/a1, nie run odzysku. |
| [Drugi odzysk](https://github.com/dlubom/jktz-mapa/actions/runs/41187188483) | 1 / `124496393833` | Sukces bez deployu i zapisu. Ewidencja identyczna bajtowo; ten sam blob SHA. |
| [Rollback A](https://github.com/dlubom/jktz-mapa/actions/runs/41187232608) | 1 / `124496515964` | Sukces z gotowego archiwum, publiczne A; B otrzymuje 15 dni ochrony. |
| [Stary Re-run B](https://github.com/dlubom/jktz-mapa/actions/runs/41186621744/attempts/2) | 2 / `124496662692` | Sukces przez jawne pominięcie starej operacji; krok 6 skipped. Ewidencja i publiczne A bez zmian. |
| [Przywrócenie original](https://github.com/dlubom/jktz-mapa/actions/runs/41187324619) | 1 / `124496785074` | Sukces kroków 6 i 8; `current=original`, brak `pending`, marker 404. |

Przed anulowaniem B obie oczekujące operacje miały status `pending`
i zero jobów. Żadna nie zastąpiła drugiej: to rzeczywisty dowód działania
`queue: max` dla dwóch oczekujących runów. Po anulowaniu obie zatrzymały
się w przygotowaniu, z pominiętymi krokami uploadu i deployu. Ewidencja
przed anulowaniem i po tych odmowach miała identyczne bajty i blob SHA
`26bd11a0ead35fd826654a6cb82bbd1fb5f7c5cf`. Normalne anulowanie zakończyło
się z opóźnieniem; nie użyto force-cancel ani kontrolowanego błędu zamiast cancel.

Odzysk sprawdził archiwa, publiczne B i sukces kroku 6 w **próbie 1**.
Ustawił ochronę A do `2026-11-15T09:00:47.674072+00:00`, dokładnie 15 dni
od potwierdzenia odzysku. Drugi odzysk pozostawił ewidencję pod tym samym
SHA `f8ca09b4a4aee30bc11046f8d701006c5257e9e9`. Po rollbacku stary Re-run B
zachował oryginalne `created_at`; zakończył się komunikatem
`Stale/already confirmed operation: no deploy`. Stan po rollbacku i Re-run
ma ten sam SHA `f080c5b539fed79a4014722ba7a939d4e1392034`.

## Przywrócenie i końcowy odczyt

- Pages: `built`, `legacy`, źródło `gh-pages:/`, HTTPS włączone, brak CNAME.
  Gałąź nadal wskazuje `12a6783bc09eda112f9f187f9df5825264bbf183`.
- Publiczne HTML, JS i CSS mają oryginalne SHA-256 z `packages.json`;
  marker `publication-probe.json` zwraca 404. Nie jest to nowy test TPN
  w przeglądarce, tylko kontrola identycznych plików.
- Workflow `402595194` ma stan `disabled_manually`. Usunięto wyłącznie
  dodaną regułę `main` ID `65006113`; pozostała oryginalna reguła
  `gh-pages` ID `65003853`. Odpowiedzi polityk przed i po są identyczne.
- Ewidencja: `current=original`, `pending=null`, brak terminu wygaśnięcia
  bieżącej paczki. Blob SHA `04026583fb9cb7c8db18ce7ba1d1bdd95e12be17`.
  A chronione do `2026-11-15T09:07:02.594821+00:00`, B do
  `2026-11-15T09:05:43.605317+00:00`. Sonda nie zawiera cleanupu.
- [Release techniczny](https://github.com/dlubom/jktz-mapa/releases/tag/pages-publication-probe-20261031),
  jego trzy assety, tag i gałąź ewidencji zostały zachowane. Ponowne pobranie
  każdego assetu po ID potwierdziło rozmiar 399 360 B i przypięte SHA-256.
  Oba odrzucone wdrożenia pozostają zapisane w `rejected_operations`.
- Brak PR-ów i aktywnych przebiegów. Nie było potrzeby ponawiać starego
  dynamicznego runu `41183308660`; powrót ustawień i bajtów potwierdzono
  bez tego awaryjnego kroku. README, 3D i sąsiednie repozytoria bez zmian.

## Weryfikacja i pozostałe luki

Ponowiono lokalną sondę (13/13), kontrolę rzeczywistego kodu kandydata
z atrapą API oraz lint YAML. `actionlint` 1.7.12 wymaga jednego jawnego
wyjątku dla nieznanego mu `concurrency.queue`; pole jest zaakceptowane
i sprawdzone na rzeczywistym GitHubie. Niezależny przegląd potwierdził
tożsamość odzyskiwanej operacji, blokadę kolejki oraz readback ewidencji.

Nie zaliczono twardego zabicia runnera ani przerwania wewnątrz POST
bez zapisanego sukcesu kroku. Taki przypadek nadal jest `unknown`, chroni
obie paczki i wymaga rozpoznania. Ręczne rozstrzygnięcie dwóch **terminalnych**
`deployment_failed` nie jest ogólną procedurą automatycznego odzysku.
Nie ustalono pojedynczej przyczyny drugiego błędu transportu: przejście
na oficjalną akcję zmieniło cały etap pakowania i uploadu.

Latest trzech źródeł, trwałe manifesty wejść, długotrwała retencja,
kasowanie po rzeczywistych 15 dniach i równoległe buildy pełnych danych
pozostają poza tą próbą. Osobno nadal brakuje testów natywnego Safari,
iPhone 14 Pro, Androida, pamięci, szwów/gutter i zwalniania zasobów.
Pełna aplikacja i kolejne zmiany działających Pages wymagają osobnego
uzgodnienia.
