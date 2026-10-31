# Publikacja Pages — weryfikacja kontraktu

**Uzupełnienie 2026-10-31:** wykonano lokalną sondę stanów i kontrolowanych
awarii oraz przygotowano nieaktywny kandydat próby GitHub. Wyniki i granice:
[raport próby](PAGES_PUBLICATION_PROBE.md). Aktualną semantykę API ponownie
sprawdzono w [notatce API](PAGES_PUBLICATION_API_CHECK.md). Próba lokalna
nie zalicza opisanych poniżej testów integracyjnych na GitHubie.

**Późniejszy stan z 2026-10-31:** po osobnej zgodzie opublikowano
[minimalną sondę TPN](PAGES_BROWSER_PROBE.md) z gałęzi `gh-pages`.
Poniższe odczyty i wnioski opisują badanie sprzed tej publikacji.
Publikacja sondy nie testuje docelowego workflow, retencji ani odzysku
przerwania i nie zmienia statusu poniższych scenariuszy integracyjnych.

Data: 2026-10-31. Etap projektowy. Wykonano odczyty dokumentacji, kodu
oficjalnej akcji i API; nie utworzono workflow, wydania ani strony.

**Wniosek:** wystarczą artefakt przypięć dla runu, gotowe paczki w Releases
i jeden plik ewidencji. Zwykłe wdrożenie może pozostać jednym kliknięciem.
Nie ma jednak potwierdzonej gwarancji automatycznego odzyskania każdego
przerwania publikacji. Wynik nieznany musi chronić obie paczki i zatrzymać
dalsze publikowanie oraz usuwanie. Poniżej oddzielono fakty od projektu.

## Sprawdzone fakty

1. Re-run zachowuje `run_id`, `GITHUB_SHA` i `GITHUB_REF`; rośnie
   `run_attempt`. Dostępny jest do 30 dni od pierwszego uruchomienia.
   Nie przypina jednak odpowiedzi z zewnętrznego API — to obowiązek
   workflow. [Zmienne](https://docs.github.com/en/actions/reference/workflows-and-actions/variables),
   [Re-run](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs).
2. Artefakty `upload-artifact` od v4 są niezmienne, ale mogą zostać usunięte
   lub zastąpione przez opcję `overwrite`. Retencja publicznego repo kończy
   się najpóźniej po 90 dniach; nie zapewnia zachowania działającej wersji
   przez dowolnie długi czas. [Akcja](https://github.com/actions/upload-artifact),
   [retencja](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization).
3. Release assets nie używają retencji artefaktów Actions. GitHub opisuje
   limit pojedynczego assetu poniżej 2 GiB i brak limitu sumy release.
   `make_latest: "false"` pozwala nie oznaczać technicznej paczki jako
   Latest. Zwykły release nie jest automatycznie niezmiennym archiwum:
   uprawniony zapis nadal wymaga kontroli. [Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases),
   [API](https://docs.github.com/en/rest/releases/releases#create-a-release).
4. Wspólna grupa concurrency obejmuje joby różnych workflow w tym samym
   repo. `queue: max` dopuszcza 100 oczekujących; domyślne `single` zastępuje
   poprzedni oczekujący. `queue: max` nie łączy się z
   `cancel-in-progress: true`. FIFO dotyczy czasu wejścia do kolejki,
   a nie kliknięcia Run workflow. [Concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).
5. Contents API przy aktualizacji wymaga SHA zastępowanego pliku; konflikt
   może zwrócić 409. To podstawa warunkowego zapisu ewidencji, nie transakcja
   obejmująca Pages. [Contents API](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents).

Stan repo odczytany na żywo: `origin` wskazuje
[`dlubom/jktz-mapa`](https://github.com/dlubom/jktz-mapa), publiczne `main`
ma SHA `5a519dc90d504ef34229e7cfb6cf82b680e9a031` zgodne z lokalnym HEAD
i `origin/main`; otwartych PR: 0; workflow: 0; `has_pages=false`.
Odczyt `/repos/dlubom/jktz-mapa/pages` zwrócił 404. Są to dane chwilowe,
nie ustawienia wdrożeniowe ustanowione przez ten raport.

## Rekomendacja: przypięcie pojedynczego runu

Nowe `workflow_dispatch`, zawsze w pierwszej próbie, odczytuje endpoint
Latest wszystkich trzech źródeł. Zapisuje odpowiedzi wybrane w tym runie,
bez sortowania wersji i bez dziedziczenia wyboru poprzedniego wdrożenia.
Nie wymaga nowego wydania wszystkich źródeł. Taką semantykę określa
specyfikacja projektu; [API Latest](https://docs.github.com/en/rest/releases/releases#get-the-latest-release)
jest źródłem wskazania GitHuba.

Należy rozdzielić dwa dokumenty:

- **Przypięcia wejść:** release/asset ID, tag i rozwiązany commit,
  oczekiwane sumy oraz ścieżki dodatkowych metadanych. Kompletny wybór
  trzech źródeł zapisać w `inputs-<run_id>` przed pobieraniem paczek;
  wyłączyć `overwrite`, ustawić 90 dni i sprawdzić odczyt zapisanych bajtów.
- **Manifest wyniku:** rzeczywiste sumy pobrań, narzędzia, przekształcenia
  i wyniki walidacji. Powstaje później, nie dopisuje pól do niezmiennego
  artefaktu przypięć. Gotowa paczka zawiera obydwa dokumenty.

Każdy Re-run odczytuje dokładnie ten artefakt, także przy ponowieniu
pojedynczego joba. Brak, uszkodzenie albo niekompletność przypięć kończy
przebieg komunikatem „Uruchom nowe Run workflow”. Dotyczy to również
awarii pierwszej próby przed trwałym zapisem: nie istnieje wtedy pełny
wybór, który można bezpiecznie odtworzyć. Nie potrzeba dziennika częściowych
odczytów Latest. Awaria samego potwierdzenia uploadu może być odzyskana
przez znalezienie i sprawdzenie kompletnego artefaktu.

Ten kontrakt zachowuje wybór, nie gwarantuje dostępności zmiennych źródeł.
Usunięty asset lub niezgodna suma zatrzymują Re-run. Ukończona paczka jest
używana ponownie bez buildu; nie wolno zastępować jej innymi bajtami pod
tym samym ID. Kolejny `run_attempt` może mieć nowy artefakt transportowy
Pages z tej samej paczki. Nie należy wiązać retencji rollbacku z transportem.

## Rekomendacja: paczki i ewidencja

Gotową paczkę oraz jej manifest przechowywać w technicznym release
`pages-<run_id>` z `make_latest: "false"`. Przed deployem potwierdzić
kompletność uploadu i SHA-256 przez odczyt z archiwum. Zapisywać konkretne
release/asset ID oraz sumy. Nie nadpisywać assetów przy ponowieniu;
istniejące bajty muszą odpowiadać zapisanemu wynikowi. To reguła workflow,
nie deklaracja włączenia funkcji GitHub immutable releases.

Jeden `state.json` na technicznej gałęzi wystarczy do przechowania:
bieżącej paczki, terminów ochrony zastąpionych paczek, ostatniej zakończonej
operacji oraz `pending`. Zapis przez Contents API z poprzednim SHA;
po niejednoznacznej odpowiedzi najpierw odczyt, bez ślepego powtórzenia.
Paczki nie trafiają do historii Git.

Reguła usuwania jest prosta: paczka bieżąca nie ma terminu wygaśnięcia;
po potwierdzonym zastąpieniu termin wynosi co najmniej 15 pełnych dni.
Rollback ponownie chroni przywróconą paczkę bezterminowo, a jej następne
zastąpienie rozpoczyna nowe 15 dni. Nieznany czas zastąpienia zastępuje się
późniejszym czasem potwierdzenia. Błąd buildu nie uruchamia tego zegara.

Sprzątanie działa tylko pod tą samą blokadą co deploy/rollback i tylko
dla znanych, zastąpionych paczek z upłyniętym terminem. Bieżąca paczka,
obie strony `pending`, kandydaci trwających operacji i nieznane wpisy
pozostają chronione. Błąd odczytu ewidencji oznacza brak usuwania. Na start
nie jest potrzebny automat kasujący osierocone, nigdy niewdrożone wydania;
można zostawić je do osobnego przeglądu. Okno 15 dni jest minimum
dostępności, nie terminem obowiązkowego usunięcia.

## Rekomendacja: kolejka i przerwanie

Finalne joby deployu, rollbacku i sprzątanie używają jednej grupy
`pages-production`, `cancel-in-progress: false`, `queue: max`.
Pod blokadą sprawdzają pierwotne `created_at` operacji względem ostatniej
zakończonej publikacji/rollbacku. Starszy run jest jawnie pomijany;
Re-run nie dostaje nowego czasu. Rollback ma czas nowego żądania.
Równe czasy i różne ID oznaczają niejednoznaczność, więc brak deployu.
Nie traktować `run_id` jako zegara ani `run_number` jako licznika wspólnego
dla różnych workflow. Pola runu udostępnia
[Actions API](https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run).

Przed wywołaniem publikacji trzeba zapisać i odczytać `pending` z obiema
paczkami, `run_id`, `run_attempt`, identyfikatorem joba i jednoznaczną nazwą
kroku publikacji. Dopiero potem uruchomić deploy, potwierdzić sukces,
zaktualizować ewidencję i wykonać test strony. Błąd tego ostatniego testu
nie cofa historii zastąpienia i nie uruchamia automatycznego rollbacku.

### Co rzeczywiście daje deploy-pages

Sprawdzono aktualne stabilne
[`actions/deploy-pages` v5.0.1](https://github.com/actions/deploy-pages/releases/tag/v5.0.1),
commit `368f82528645a54fb793d4d04e342629a3f51346`:

- [`action.yml`](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/action.yml)
  deklaruje tylko output `page_url`.
- [`src/index.js`](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/index.js)
  ustawia URL **przed** odpytywaniem końcowego statusu. Sam URL nie jest
  potwierdzeniem wdrożenia.
- [`deployment.js`](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/deployment.js)
  trzyma ID w pamięci i wypisuje je do logu. Sukces zgłasza po stanie
  `succeed`; przy timeout/cancel próbuje anulować wdrożenie. Próba anulowania
  nie dowodzi, że strona nie została wcześniej zastąpiona.
- [`context.js`](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/context.js)
  używa `GITHUB_SHA` jako `pages_build_version`. Dwa wdrożenia różnych
  danych przy tym samym commicie aplikacji mają więc ten sam klucz.

[Pages API](https://docs.github.com/en/rest/pages/pages#create-a-github-pages-deployment)
zwraca ID i pozwala pytać o status po ID lub commit SHA. Nie opisuje
idempotency key dla POST ani wyszukiwania publikacji po `run_id`.
Odzyskiwanie wyłącznie przez SHA aplikacji byłoby niejednoznaczne.
Nie wolno też mylić ogólnego deploymentu środowiska GitHub z identyfikatorem
konkretnego wdrożenia Pages bez dowodu ich powiązania.

### Najprostsza ścieżka do sprawdzenia

**Wniosek z kodu i API, jeszcze nie wynik testu:** przerwanie po udanym
kroku deploy, lecz przed zapisem ewidencji można próbować uzgodnić bez
forka akcji. [Jobs API dla konkretnej próby](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run-attempt)
zwraca joby i `steps[].conclusion`. Trwały `pending` pozwala odszukać
właściwy job/krok, sprawdzić jego `success` i porównać identyfikator oraz
hash manifestu strony z oczekiwaną paczką. Zapisać późniejszy czas
potwierdzenia, dzięki czemu okres ochrony się nie skróci. Publikacja musi
być osobnym krokiem przypiętej akcji, bez `continue-on-error`; odnalezienie
właściwego kroku nie może polegać na wyborze ostatniego zielonego joba.

Nie wystarcza zielony cały workflow ani sam manifest strony. Przerwanie
wewnątrz kroku może nastąpić po zaakceptowanym POST, zanim ID lub sukces
utrwalą się w historii. Stary lub chwilowo niedostępny manifest nie
dowodzi niepowodzenia; ponowny odczyt wersji znanej z dawnego rollbacku
także nie identyfikuje konkretnej operacji. Brak historii, sprzeczność,
timeout i niepotwierdzony cancel pozostawiają stan **unknown**. Wtedy
blokujemy nowe publikacje i sprzątanie, zachowujemy obie paczki oraz
raportujemy potrzebę odzyskania stanu. Nie ponawiamy POST automatycznie.

To ogranicza złożoność, ale pozostawia ręczne rozpoznanie rzadkiej awarii.
Jeżeli wymagane będzie automatyczne odzyskiwanie także tego przypadku,
potrzebna jest osobna próba małego adaptera Pages API z trwałym ID;
sam zapis odpowiedzi POST nadal nie usuwa przerwy między przyjęciem
żądania a utrwaleniem odpowiedzi. Nie ma podstaw, aby obecnie obiecać
pełne odzyskiwanie lub implementować własny orkiestrator publikacji.

## Testy przed uznaniem mechanizmu za gotowy

Żadnego poniższego testu integracyjnego nie wykonano. Wymagają później
osobno dopuszczonego workflow i testowego wdrożenia Pages.

| Próba | Wymagany wynik |
| --- | --- |
| Nowe Latest jednego źródła między kliknięciami | Nowy run pobiera je, zachowując aktualne Latest pozostałych źródeł. |
| Latest zmienia się przed Re-run każdego rodzaju | Zero ponownych odczytów Latest; identyczne przypięcia. |
| Przerwanie przed/po uploadzie przypięć, utrata odpowiedzi | Użycie wyłącznie kompletnego zapisu albo jawny nakaz nowego runu. |
| Zmieniony/usunięty asset, niezgodny hash gotowej paczki | Błąd bez wyboru zastępstwa i bez deployu. |
| Dwa buildy oraz rollback w odwrotnej kolejności ukończenia | Jedna publikacja naraz; stary run nie nadpisuje późniejszej zakończonej operacji. |
| A działa 120 dni, potem A→B→A→B | A jest dostępne przez cały czas używania; każde zastąpienie daje nowe pełne 15 dni. |
| Kill po sukcesie kroku deploy, przed aktualizacją ewidencji | Jobs API wskazuje dokładny krok/próbę; zgodny odczyt paczki pozwala uzgodnić stan. |
| Kill wewnątrz deployu po POST; brak ID, timeout/cancel | Obie paczki zachowane; unknown blokuje publikację i usuwanie. |
| Dwie paczki przy tym samym SHA aplikacji | Nigdy nie wybieramy wdrożenia wyłącznie po SHA. |
| Konflikt/utrata odpowiedzi zapisu ewidencji; niedostępna historia | Odczyt i uzgodnienie albo zatrzymanie; brak skrócenia ochrony. |

Próby lokalne z atrapą API mogą sprawdzić logikę stanów i retencji.
Nie potwierdzą zachowania GitHub podczas zabicia runnera, zapisu wyników
kroków, propagacji Pages ani czasu dostępności historii po awarii.
