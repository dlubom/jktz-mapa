# Próba publikacji na GitHub — dziennik wykonania

Data: 2026-10-31. Użytkownik zatwierdził zakres
[przygotowanej próby](probes/publication/GITHUB_TRIAL.md): techniczny release,
gałąź ewidencji, ręczny workflow, czasową konfigurację Pages i przywrócenie
oryginalnej sondy. To nie zgoda na pełną aplikację.

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
po poprawce. Kolejny commit pozwala też odróżnić endpoint statusu Pages
od pierwszego nieudanego wdrożenia. Wynik następnej próby rozstrzygnie
skuteczność poprawki na GitHubie.

Dowody robocze: `/private/tmp/jktz-publication-live-20261031-gwtjdqyu`.
Po zakończeniu ograniczony zestaw dowodów i wynik przywrócenia trafią
do repozytorium. Próba trwa; nie jest jeszcze zaliczona.
