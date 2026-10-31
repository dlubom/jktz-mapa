# Minimalna próba publikacji — aktualne API i ograniczenia

Sprawdzenie: 2026-10-31. Tylko odczyty GitHuba, dokumentacji i kodu akcji.
Nie zmieniono ustawień Pages, workflow ani gałęzi. Poniższa próba wymaga
osobnej zgody; sprawdzenie API nie zalicza odzyskania po przerwaniu.

## Fakty sprawdzone teraz

- Odczyt [`GET /pages`](https://api.github.com/repos/dlubom/jktz-mapa/pages):
  `build_type=legacy`, `source={branch: gh-pages, path: /}`,
  `https_enforced=true`, `cname=null`, `status=built`.
  [`gh-pages`](https://github.com/dlubom/jktz-mapa/tree/12a6783bc09eda112f9f187f9df5825264bbf183)
  nadal wskazuje `12a6783bc09eda112f9f187f9df5825264bbf183`.
- [`41183308660`](https://github.com/dlubom/jktz-mapa/actions/runs/41183308660)
  jest **ID runu Actions**, nie udowodnionym ID wdrożenia Pages.
  Odczyt API: `event=dynamic`, `path=dynamic/pages/pages-build-deployment`,
  `head_branch=gh-pages`, `head_sha=12a6783bc09eda112f9f187f9df5825264bbf183`,
  próba 1, sukces. Jej job `deploy` ma ID `124485039774`; krok numer 2
  `Deploy to GitHub Pages` jest `completed/success`.
- Odczyt [polityk środowiska `github-pages`](https://api.github.com/repos/dlubom/jktz-mapa/environments/github-pages/deployment-branch-policies)
  zwrócił jedną regułę: `gh-pages`, `type=branch`, ID `65003853`.
  Próba z `main` wymaga czasowego dodania osobnej reguły `main`; zapisać
  jej zwrócone ID i po próbie usunąć wyłącznie tę nowo utworzoną regułę.
  Nie usuwać ani nie zastępować istniejącej reguły `gh-pages`.
- Latest [`actions/deploy-pages` v5.0.1](https://github.com/actions/deploy-pages/releases/tag/v5.0.1)
  oraz odczyt refa tagu wskazują commit
  `368f82528645a54fb793d4d04e342629a3f51346`. Taki pełny SHA należy umieścić
  w przygotowywanym YAML.

## Tożsamość kroku i odczyt historii

Właściwy endpoint to
`GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/jobs`.
Query obsługuje `per_page` (maksimum 100) i `page`; nie ma filtra po nazwie
joba/kroku. Trzeba obsłużyć paginację. Zwykły `/runs/{run_id}/jobs` ma
`filter=latest|all`, domyślnie `latest`; ten wariant nie zastępuje wskazania
próby. [`Jobs API`](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run-attempt)
zwraca `steps[].name`, `number`, `status`, `conclusion` i czasy, ale nie
YAML-owe `steps[].id`.

**Zalecenie dla sondy:** przed deployem odszukać dokładnie jeden job bieżącej
próby, zapisać jego numeryczne ID, jawne unikalne `name`, numer i nazwę
kroku deployu, `run_id`, `run_attempt`, SHA workflow oraz tożsamość obu paczek.
`GITHUB_JOB` oznacza klucz joba w YAML, np. `publish`, a nie numeryczne ID
REST. [Zmienne](https://docs.github.com/en/actions/reference/workflows-and-actions/variables).
Brak widocznego joba można odpytywać przez ograniczony czas; brak lub
wieloznaczność po tym czasie blokuje deploy.

Odzysk sprawdza zapisany job w zapisanej próbie i dokładnie jeden wskazany
krok `completed/success`, następnie oczekiwane bajty publicznego manifestu.
Zielony job/workflow ani sam manifest nie wystarczają. Próbę można uzgodnić
mimo czerwonego/anulowanego całego joba, jeżeli sukces deployu jest
jednoznacznie zapisany. To proponowana reguła sondy, jeszcze bez testu
przerwania na GitHubie.

## Akcja, współbieżność i granica odzyskiwania

[`action.yml`](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/action.yml)
deklaruje tylko `page_url`.
[`index.js`](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/index.js)
ustawia URL przed końcowym odpytywaniem, a
[`deployment.js`](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/deployment.js)
uznaje sukces po `status=succeed`. ID pozostaje w pamięci i logu.
Kod ustawia także niedeklarowany output `status`; sonda nie powinna
opierać trwałego odzysku na outputach utraconego runnera.
[`context.js`](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/context.js)
bierze wersję buildu z `GITHUB_SHA`: różne paczki mogą mieć ten sam SHA.

Wszystkie operacje zmieniające stronę i ewidencję wymagają tej samej
stałej grupy concurrency z `cancel-in-progress: false`, `queue: max`.
Maksimum to 100 oczekujących; następne są anulowane. Domyślne `single`
zastępuje poprzednią oczekującą operację. FIFO dotyczy wejścia do kolejki,
nie czasu kliknięcia. Grupa nie blokuje działań administracyjnych poza
workflow. [Dokumentacja concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

Anulowanie workflow wysyła sygnały i może ostatecznie zabić procesy;
`always()` może utrzymać job przy życiu. Nie daje to transakcji z Pages
ani gwarancji wykonania porządkowania.
[Przebieg anulowania](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation).
Akcja próbuje anulować Pages przy timeout/sygnale, ale utrata odpowiedzi
POST nadal pozostawia lukę. Pages API nie dokumentuje idempotency key ani
wyszukiwania deployu po `run_id`.
[API wdrożeń](https://docs.github.com/en/rest/pages/pages#create-a-github-pages-deployment).
Wniosek: brak zapisanego sukcesu, sprzeczność lub niedostępna historia
oznaczają `unknown`; obie paczki pozostają chronione, bez ponawiania
deployu i bez kasowania.

## Minimalna próba A → B → A do zatwierdzenia

1. Zachować pełną kopię drzewa pod przypiętym SHA `gh-pages`, konfigurację
   Pages i inwentarz sum. A oraz B zawierają wszystkie oryginalne pliki
   sondy bez zmian; różni je tylko nowy plik manifestu próby. Nie publikować
   pustej strony zastępczej ani samego manifestu. Archiwum oryginału
   nie zawiera dodatkowego pliku i służy do końcowego przywrócenia.
2. Przygotować ręczny workflow i techniczną ewidencję. `workflow_dispatch`
   wymaga pliku na domyślnej gałęzi; samo wypchnięcie gałęzi testowej nie
   wystarczy. [Składnia](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_dispatch).
   Job publikujący potrzebuje `pages: write`, `id-token: write`, środowiska
   `github-pages`; odczyt historii dodatkowo `actions: read`, zapis ewidencji
   `contents: write`. [Workflow Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
   Minimalny kandydat może pozostać nieaktywnym plikiem
   `doc/probes/publication/github-candidate.yml` do zatwierdzenia. Zalecane
   archiwum próby: jeden techniczny release z trzema gotowymi paczkami
   (oryginał, A, B), osobna gałąź ewidencji, bez automatycznego usuwania.
3. Po zgodzie przestawić Pages na `workflow`; wdrożyć A normalnie.
   Dla B zapisać i odczytać `pending` **przed** osobnym krokiem
   `deploy-pages`, bez `continue-on-error`.
4. Po sukcesie deployu B wejść w nazwany krok oczekiwania przed zapisem
   ewidencji. Odczytem API potwierdzić sukces deployu i aktywne oczekiwanie,
   następnie anulować run. Zapis ewidencji nie ma `always()`; `pending`
   ma pozostać. Wariant `exit 42` w tym miejscu sprawdza zwykły błąd kroku,
   nie zastępuje cancel ani utraty runnera.
5. Osobną operacją pod tą samą blokadą uzgodnić B przez zapisaną próbę,
   job, krok i publiczny manifest. Zapisać późniejszy czas potwierdzenia;
   odczytać ewidencję ponownie. Powtórne uzgodnienie nie uruchamia deployu
   ani nie przesuwa już zapisanego czasu. Następnie przywrócić gotowe A
   bez buildu i potwierdzić stronę oraz ewidencję.

To bada anulowanie **po** ukończeniu kroku. Nagła utrata runnera oraz
przerwanie **wewnątrz** POST/deployu pozostają osobnymi brakami dowodów.
Nie zaliczać ich na podstawie tej próby ani lokalnej atrapy.

## Przywrócenie istniejącej sondy

Zmiana ustawień używa `PUT /repos/dlubom/jktz-mapa/pages` z
`{"build_type":"workflow"}`. Powrót:
`{"build_type":"legacy","source":{"branch":"gh-pages","path":"/"}}`.
To operacja administracyjna; API wskazuje uprawnienia Pages i Administration
write. Nie zmieniać `cname`/HTTPS ani zawartości `gh-pages`.
Odpowiedź 204 potwierdza zmianę ustawień, nie gotową stronę.
[API ustawień Pages](https://docs.github.com/en/rest/pages/pages#update-information-about-a-github-pages-site).

Zalecana kolejność końcowa: zatrzymać nowe próby i poczekać na zakończenie
wszystkich już wysłanych wdrożeń; w trybie workflow przywrócić archiwum
oryginału i sprawdzić sumy publicznych plików; następnie przywrócić
ustawienia `legacy`, odczytać je i ponownie sprawdzić stronę. Nie wolno
uruchamiać tej ścieżki w ciemno, jeżeli nieznane wdrożenie może nadal działać.
Na końcu odtworzyć listę reguł środowiska przez usunięcie tylko reguły
utworzonej dla próby i sprawdzić, że zachowano regułę `65003853`.

Jeżeli publikacja z przywróconej gałęzi wymaga wznowienia, dokumentacja
publikacji gałęziowej wskazuje re-run jej workflow jako ścieżkę naprawy.
[Źródło publikacji](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
Zapisany run `41183308660` daje konkretny fallback z oryginalnym SHA;
re-run jest dostępny przez 30 dni, zachowuje SHA/ref i wymaga dostępnego
workflow. [Re-run](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs).
Jego wykonanie i odczyt publicznych sum muszą być częścią zatwierdzonej
próby, jeżeli fallback okaże się potrzebny; nie testowano go teraz.
Samo `GET /pages: built` ani zachowana gałąź nie dowodzą odtworzenia strony.
