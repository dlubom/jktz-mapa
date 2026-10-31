# Procedura zatwierdzonej próby GitHub

Procedurę przygotowano i zatwierdzono 2026-10-31. Rzeczywisty przebieg,
odstępstwa i wynik przywrócenia zapisano w
[raporcie wykonania](../../PAGES_PUBLICATION_GITHUB_TRIAL.md).
Kopia YAML została zainstalowana w `.github/workflows` do tej ograniczonej
próby. Poniższe polecenia zachowują procedurę; nie należy ponownie
inicjalizować istniejącego release ani ewidencji. Kolejna próba zmieniająca
Pages wymaga nowego uzgodnienia. Lokalna atrapa zaliczyła 13 scenariuszy
(`local-results.json`); jej wynik pozostaje odrębny od dowodu GitHub.

## Konkretny zakres do zatwierdzenia

- Instalacja jednego ręcznego workflow `pages-publication-probe.yml` na `main`
  oraz jego dwóch skryptów i przypiętego `packages.json`; bez aplikacji.
- Jeden techniczny release `pages-publication-probe-20261031`,
  `make_latest: false`, z `original.tar`, `A.tar`, `B.tar` po 399 360 B.
  Tag wskazuje zatwierdzony commit kodu próby. Żadnego zastępowania assetów.
- Gałąź `pages-probe-state` z `state.json`, aktualizowanym warunkowym PUT
  Contents API z poprzednim SHA oraz odczytem potwierdzającym.
- Czasowa dodatkowa reguła środowiska `github-pages` dla `main`;
  istniejąca reguła `gh-pages` ID `65003853` pozostaje.
- Czasowa zmiana Pages z `legacy` na `workflow`, publikacje A → B,
  anulowanie B po sukcesie kroku deployu, jawny odzysk, rollback A,
  odrzucenie starego Re-run, publikacja oryginału i powrót do `legacy`.
  Dwie oczekujące operacje sprawdzą kolejkę oraz blokadę przez `pending`.
- Po próbie: wyłączenie tego workflow, usunięcie wyłącznie nowej reguły
  środowiska i odczyt ustawień/strony. Release, paczki, gałąź ewidencji,
  tag i `gh-pages` zostają. Nie ma kodu usuwającego paczki.
- Jeżeli powrót do publikacji gałęziowej wymaga wznowienia: jednorazowy
  Re-run istniejącego runu `41183308660`, po sprawdzeniu jego SHA/ref
  i dostępności Re-run (30 dni). Nie wolno go uruchomić przy aktywnym
  lub nierozwiązanym wdrożeniu próby.

Wymagane są Python 3, Git, `gh` oraz dostęp operatora do Contents, Actions,
Releases, Pages i Administration write (ustawienia/reguła środowiska).
Job używa `contents: write`, `actions: read`, `pages: write`,
`id-token: write`; checkout nie zachowuje poświadczeń. Pozostałe joby lub
ręczne zmiany Pages trzeba zatrzymać organizacyjnie: concurrency nie
blokuje administratora ani starego workflow publikacji gałęziowej.

## Co jest przypięte

Oryginał to pełne drzewo `12a6783bc09eda112f9f187f9df5825264bbf183`:
trzy publiczne pliki z `remote-before.json` i pusty `.nojekyll`.
A/B dodają wyłącznie `publication-probe.json`; aplikacja i zasoby TPN
mają te same bajty. Oryginał nie ma markera. `prepare_packages.py` odczytuje
bloby z konkretnego SHA, sprawdza cały inwentarz oraz sumy i buduje USTAR
ze stałą kolejnością, mtime 0, uid/gid 0 i trybem 0644. Wynik musi być
identyczny z recenzowanym `packages.json`.

Runtime pobiera asset po zapisanym ID, sprawdza SHA-256 i cały tar, po czym
sprawdza również dostępność archiwum bieżącej strony (drogi powrotu).
Zweryfikowane pliki trafiają do nowego katalogu `site`, z zachowaniem
całego inwentarza, bajtów i `.nojekyll`. Transport tworzy przypięta
oficjalna `actions/upload-pages-artifact` v5.0.0, z `include-hidden-files=true`.
Archiwa w release pozostają niezmienne. Pierwsza własna serializacja nie
miała wymaganego prefiksu `./`; sama jego korekta nie usunęła błędu Pages,
dlatego transport przekazano implementacji referencyjnej.
[Wymaganie i wskazanie implementacji](https://github.com/actions/deploy-pages/issues/203#issuecomment-1652804586).
Artefakt Actions jest tylko transportem o retencji jednego dnia;
rollback używa gotowego assetu release. `upload-pages-artifact` v5.0.0 ma
SHA `fc324d3547104276b827a68afc52ff2a11cc49c9` (wewnętrzny `upload-artifact`
v7.0.0 także przypięty przez autora akcji), checkout v4.2.2 ma pełny SHA;
`deploy-pages` v5.0.1 jest
przypięte do `368f82528645a54fb793d4d04e342629a3f51346`.

Przed deployem zapisuje się obie paczki, pierwotne `created_at`, run ID,
attempt, head SHA, numeryczne job ID, unikalną nazwę joba i krok nr 6
`Publish Pages probe`. Zmiana kolejności kroków wymaga zmiany i ponownego
sprawdzenia tej liczby. Historia jest pobierana z paginowanego endpointu
**konkretnej próby**. Zielony cały job nie jest warunkiem odzysku.

Próba GitHub potwierdziła widoczność przyszłego kroku nr 6
już w fazie zapisu `pending`. Runtime czeka na nią najwyżej sześć
odczytów z odstępem pięciu sekund; brak/wieloznaczność zatrzymują próbę
przed deployem. Odzysk ponownie sprawdza oba zachowane archiwa.

## 1. Lokalne przygotowanie i kontrola stanu (bez publikacji)

Poniższe bloki zakładają `cwd` repozytorium i wspólną sesję powłoki.
Katalog roboczy jest nowy; istniejące paczki nie są nadpisywane.
Uruchomić **dedykowaną powłokę** poleceniem `zsh -f`, a w niej najpierw
`set -euo pipefail`. Wszystkie bloki wykonywać w tej powłoce; dowolny
nieoczekiwany błąd kończy ją przed następnym poleceniem. Po błędzie nie
kontynuować kolejnego bloku ani inicjalizacji: odczytać rzeczywisty stan
i zachowany `PROBE_DIR`. Wyjątkiem są trzy jawnie sprawdzane 404 poniżej.

```sh
set -euo pipefail
export PROBE_REPO=dlubom/jktz-mapa
export PROBE_TAG=pages-publication-probe-20261031
export PROBE_DIR="$(mktemp -d /private/tmp/jktz-publication-trial.XXXXXX)"
git clone --no-checkout --single-branch --branch gh-pages \
  https://github.com/dlubom/jktz-mapa.git "$PROBE_DIR/source"
python3 doc/probes/publication/prepare_packages.py \
  --source-repo "$PROBE_DIR/source" --output "$PROBE_DIR/packages"
python3 doc/probes/publication/github_probe.py check-public original
gh api --method GET "repos/$PROBE_REPO/pages" > "$PROBE_DIR/pages-before.json"
gh api --method GET "repos/$PROBE_REPO/environments/github-pages/deployment-branch-policies" \
  > "$PROBE_DIR/policies-before.json"
gh api --method GET "repos/$PROBE_REPO/git/ref/heads/gh-pages" > "$PROBE_DIR/branch-before.json"
gh run list --repo "$PROBE_REPO" --limit 100 --json databaseId,status,workflowName,headSha
python3 - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ['PROBE_DIR'])
s = json.loads((p/'pages-before.json').read_text())
assert s['build_type']=='legacy' and s['source']=={'branch':'gh-pages','path':'/'}
assert s['cname'] is None and s['https_enforced'] is True
assert json.loads((p/'branch-before.json').read_text())['object']['sha']=='12a6783bc09eda112f9f187f9df5825264bbf183'
rules = json.loads((p/'policies-before.json').read_text())['branch_policies']
assert len(rules)==1 and rules[0]['id']==65003853 and rules[0]['name']=='gh-pages'
PY
```

STOP przy jakiejkolwiek zmianie względem tych warunków lub aktywnym
wdrożeniu. Odczytać brak tagu/release i `pages-probe-state`: odpowiedź
404 oznacza brak; 403/timeout nie są dowodem braku. Istniejących zasobów
nie resetować ani nie zastępować — najpierw sprawdzić ich pochodzenie.

```sh
python3 - <<'PY'
import os, subprocess
repo, tag = os.environ['PROBE_REPO'], os.environ['PROBE_TAG']
for suffix in (f'releases/tags/{tag}', f'git/ref/tags/{tag}', 'git/ref/heads/pages-probe-state'):
 result = subprocess.run(['gh','api','--method','GET',f'repos/{repo}/{suffix}'], capture_output=True, text=True)
 assert result.returncode != 0 and 'HTTP 404' in result.stderr, (suffix, result.stdout, result.stderr)
 print('Confirmed absent:', suffix)
PY
```

## 2. Po zgodzie: instalacja, archiwum i ewidencja

Uzgodniony commit/PR ma obejmować wyłącznie pliki próby i wymagane już
zrecenzowane dokumenty. Przed commitem sprawdzić zastane zmiany, branch
rules i diff. Jeśli `main` wymaga PR, zastosować obowiązującą ścieżkę;
zgoda na próbę nie oznacza obchodzenia ochrony gałęzi.

```sh
mkdir -p .github/workflows
cp doc/probes/publication/github-candidate.yml .github/workflows/pages-publication-probe.yml
git add .github/workflows/pages-publication-probe.yml \
  doc/probes/publication/github_probe.py doc/probes/publication/prepare_packages.py \
  doc/probes/publication/packages.json doc/probes/publication/remote-before.json
git diff --cached --check
git diff --cached
```

Po zatwierdzonym dostarczeniu tego diffu na `main` sprawdzić odczytem
workflow, zapisać SHA i utworzyć release. Nowa gałąź ewidencji startuje
od tego commitu (zawiera też jego drzewo; nie jest gałęzią publikacji).

```sh
export PROBE_HEAD="$(gh api --method GET "repos/$PROBE_REPO/git/ref/heads/main" --jq .object.sha)"
gh api --method GET "repos/$PROBE_REPO/contents/.github/workflows/pages-publication-probe.yml?ref=$PROBE_HEAD" \
  > "$PROBE_DIR/installed-workflow.json"
python3 - <<'PY'
import base64, json, os
from pathlib import Path
p=Path(os.environ['PROBE_DIR'])
assert base64.b64decode(json.loads((p/'installed-workflow.json').read_text())['content']) == Path('doc/probes/publication/github-candidate.yml').read_bytes()
(p/'release-request.json').write_text(json.dumps({'tag_name':os.environ['PROBE_TAG'],
 'target_commitish':os.environ['PROBE_HEAD'],'name':'Pages publication probe 2026-10-31',
 'body':'Technical publication recovery trial. Preserve original, A and B archives.',
 'draft':False,'prerelease':False,'make_latest':'false'}))
(p/'branch-request.json').write_text(json.dumps({'ref':'refs/heads/pages-probe-state','sha':os.environ['PROBE_HEAD']}))
PY
gh api --method POST "repos/$PROBE_REPO/releases" --input "$PROBE_DIR/release-request.json" > "$PROBE_DIR/release-created.json"
gh release upload "$PROBE_TAG" --repo "$PROBE_REPO" \
  "$PROBE_DIR/packages/original.tar" "$PROBE_DIR/packages/A.tar" "$PROBE_DIR/packages/B.tar"
gh api --method GET "repos/$PROBE_REPO/releases/tags/$PROBE_TAG" > "$PROBE_DIR/release.json"
python3 doc/probes/publication/github_probe.py initial-state "$PROBE_DIR/release.json" > "$PROBE_DIR/state.json"
gh api --method POST "repos/$PROBE_REPO/git/refs" --input "$PROBE_DIR/branch-request.json" > "$PROBE_DIR/branch-created.json"
python3 - <<'PY'
import base64, json, os
from pathlib import Path
p=Path(os.environ['PROBE_DIR'])
(p/'state-request.json').write_text(json.dumps({'branch':'pages-probe-state',
 'message':'Initialize publication probe ledger', 'content':base64.b64encode((p/'state.json').read_bytes()).decode()}))
PY
gh api --method PUT "repos/$PROBE_REPO/contents/state.json" --input "$PROBE_DIR/state-request.json" > "$PROBE_DIR/state-created.json"
gh api --method GET "repos/$PROBE_REPO/contents/state.json?ref=pages-probe-state" > "$PROBE_DIR/state-readback.json"
python3 - <<'PY'
import base64, json, os
from pathlib import Path
p=Path(os.environ['PROBE_DIR'])
assert base64.b64decode(json.loads((p/'state-readback.json').read_text())['content'])==(p/'state.json').read_bytes()
PY
```

W tej jednorazowej inicjalizacji PUT **tworzy** nieistniejący plik, dlatego
nie ma SHA. Wszystkie późniejsze aktualizacje mają poprzedni SHA. Przy
błędzie/utracie odpowiedzi dowolnego zapisu: STOP, odczyt zasobu po nazwie,
sprawdzenie ID i bajtów; żadnego ślepego ponowienia POST/PUT/uploadu ani
`--clobber`. `initial-state` odczytuje wszystkie trzy assety po ID i
weryfikuje całe archiwa przed przygotowaniem ewidencji.

## 3. Po zgodzie: czasowa konfiguracja Pages

```sh
gh api --method POST "repos/$PROBE_REPO/environments/github-pages/deployment-branch-policies" \
  -f name=main -f type=branch > "$PROBE_DIR/main-policy-created.json"
export PROBE_MAIN_POLICY_ID="$(python3 -c 'import json,os; print(json.load(open(os.environ["PROBE_DIR"]+"/main-policy-created.json"))["id"])')"
printf '%s\n' "$PROBE_MAIN_POLICY_ID" > "$PROBE_DIR/main-policy-id.txt"
gh api --method GET "repos/$PROBE_REPO/environments/github-pages/deployment-branch-policies"
gh api --method PUT "repos/$PROBE_REPO/pages" -f build_type=workflow
gh api --method GET "repos/$PROBE_REPO/pages" > "$PROBE_DIR/pages-workflow.json"
python3 - <<'PY'
import json, os
p=json.load(open(os.environ['PROBE_DIR']+'/pages-workflow.json'))
assert p['build_type']=='workflow' and p['cname'] is None and p['https_enforced'] is True
PY
```

Zachować cały `PROBE_DIR`, szczególnie nowe ID reguły. Gdy odpowiedź jej
utworzenia zaginie, porównać listę reguł z zapisem sprzed próby; nie
tworzyć drugiej reguły. Nigdy nie usuwać `65003853`.

## 4. Sekwencja kontrolowanej próby

Dispatch wykonywać wyłącznie z `main`, bez równoległych działań operatora.
Po każdym wywołaniu `gh workflow run` odczytać listę runów i zapisać
**konkretne** ID z nazwą workflow, czasem i SHA `PROBE_HEAD`. CLI nie jest
traktowane jako źródło potwierdzenia deployu. Przed następnym etapem
czekać na terminalny status wskazanego runu, z wyjątkiem opisanej kolejki.

```sh
gh workflow run pages-publication-probe.yml --repo "$PROBE_REPO" --ref main -f operation=publish-A -f pause_after_deploy=false
gh run list --repo "$PROBE_REPO" --workflow pages-publication-probe.yml --limit 10 --json databaseId,createdAt,status,conclusion,headSha
```

Po ukończeniu A: sukces kroku deployu, `current=A`, `pending=null`,
publiczny marker A i trzy bazowe sumy. B uruchomić z pauzą:

```sh
gh workflow run pages-publication-probe.yml --repo "$PROBE_REPO" --ref main -f operation=publish-B -f pause_after_deploy=true
gh run list --repo "$PROBE_REPO" --workflow pages-publication-probe.yml --limit 10 --json databaseId,createdAt,status,conclusion,headSha
read -r 'PROBE_B_RUN?ID uruchomienia publish-B z powyższej listy: '
export PROBE_B_RUN
gh api --method GET "repos/$PROBE_REPO/actions/runs/$PROBE_B_RUN/attempts/1/jobs?per_page=100" > "$PROBE_DIR/B-jobs.json"
```

Przed anulowaniem wymagane: dokładnie jeden job tej próby, krok
`Publish Pages probe`, nr 6, `completed/success`, następny krok
`Pause after successful B deploy` w `in_progress`. Jeśli to jeszcze nie
nastąpiło, ponowić **GET**. Pauza trwa 300 sekund; jeżeli minęła i
ewidencja została zapisana, ten run nie zalicza testu anulowania.

Gdy B czeka, wysłać dwie operacje `publish-A`, zachowując oba ID. Ich
pierwotne czasy muszą być różne — odstęp dwóch sekund ułatwia odróżnienie.
Obie powinny czekać na wspólnej grupie, bez zastąpienia pierwszej:

```sh
gh workflow run pages-publication-probe.yml --repo "$PROBE_REPO" --ref main -f operation=publish-A -f pause_after_deploy=false
sleep 2
gh workflow run pages-publication-probe.yml --repo "$PROBE_REPO" --ref main -f operation=publish-A -f pause_after_deploy=false
gh run list --repo "$PROBE_REPO" --workflow pages-publication-probe.yml --limit 10 --json databaseId,createdAt,status,conclusion,headSha
gh run cancel "$PROBE_B_RUN" --repo "$PROBE_REPO"
```

Po zakończeniu B oba oczekujące runy mają się zakończyć błędem
`pending/unknown: run explicit recover...`, bez deployu. Zapisać ich
pełną historię i ewidencję: `current=A`, `pending.to=B`. Potwierdzić,
że B ma anulowany job/run, lecz krok deployu nadal ma `success`.
`exit 42`, zwykły błąd kroku i upłynięcie pauzy nie zastępują anulowania.

```sh
gh api --method GET "repos/$PROBE_REPO/actions/runs/$PROBE_B_RUN/attempts/1/jobs?per_page=100" > "$PROBE_DIR/B-cancelled-jobs.json"
gh api --method GET "repos/$PROBE_REPO/contents/state.json?ref=pages-probe-state" > "$PROBE_DIR/pending-B.json"
gh workflow run pages-publication-probe.yml --repo "$PROBE_REPO" --ref main -f operation=recover -f pause_after_deploy=false
```

Po zakończeniu odzysku: `current=B`, `pending=null`, A chronione do
`confirmed_at + 15 dni`. Odzysk nie wysyła deployu. Zapisać ewidencję,
uruchomić `recover` drugi raz i porównać bajty oraz blob SHA ewidencji;
muszą pozostać identyczne (bez przesunięcia czasu ochrony).

```sh
gh api --method GET "repos/$PROBE_REPO/contents/state.json?ref=pages-probe-state" > "$PROBE_DIR/recovered-B.json"
gh workflow run pages-publication-probe.yml --repo "$PROBE_REPO" --ref main -f operation=recover -f pause_after_deploy=false
```

Po drugim odzysku i kontroli identyczności wykonać rollback A, zaczekać
na sukces i sprawdzić marker/sumy/ewidencję. Następnie ponowić **cały**
stary run B: nie `--failed` ani pojedynczy job.

```sh
gh workflow run pages-publication-probe.yml --repo "$PROBE_REPO" --ref main -f operation=rollback-A -f pause_after_deploy=false
# Dopiero po potwierdzonym zakończeniu rollbacku:
gh run rerun "$PROBE_B_RUN" --repo "$PROBE_REPO"
```

Stary B ma zachować pierwotne `created_at` i zakończyć się bez deployu,
z komunikatem `Stale/already confirmed operation`. Ewidencja A oraz jej
czasy muszą zostać identyczne. B jest chronione przez kolejne pełne 15 dni,
A bezterminowo. Ten probe ma jeden job; ograniczenie do pełnego Re-run
nie testuje wszystkich wariantów ponawiania workflow produkcyjnego.

## 5. Przywrócenie — obowiązkowe zakończenie próby

Najpierw zakończyć wszystkie runy/kolejkę i rozwiązać każdy `pending`
przez jawne `recover`. Przy unknown nie publikować oryginału w ciemno,
nie resetować ewidencji ani ustawień i niczego nie usuwać. Zapisany sukces
konkretnego kroku plus zgodne publiczne bajty są minimalnym dowodem
odzysku; brak historii/sprzeczność oznaczają STOP do ręcznego wyjaśnienia.

```sh
gh run list --repo "$PROBE_REPO" --limit 100 --json databaseId,status,workflowName
gh api --method GET "repos/$PROBE_REPO/contents/state.json?ref=pages-probe-state"
gh workflow run pages-publication-probe.yml --repo "$PROBE_REPO" --ref main -f operation=restore-original -f pause_after_deploy=false
```

Po terminalnym sukcesie oryginału: ewidencja `current=original`,
`pending=null`, exact deploy step success i publiczne trzy sumy zgodne;
`publication-probe.json` zwraca 404. Sprawdzić brak pozostałych aktywnych
runów i dopiero wtedy wyłączyć sondę, przywrócić Pages i sprawdzić stronę:

```sh
python3 doc/probes/publication/github_probe.py check-public original
gh workflow disable pages-publication-probe.yml --repo "$PROBE_REPO"
python3 - <<'PY'
import json, os
from pathlib import Path
(Path(os.environ['PROBE_DIR'])/'pages-restore.json').write_text(json.dumps({
 'build_type':'legacy','source':{'branch':'gh-pages','path':'/'}}))
PY
gh api --method PUT "repos/$PROBE_REPO/pages" --input "$PROBE_DIR/pages-restore.json"
gh api --method GET "repos/$PROBE_REPO/pages" > "$PROBE_DIR/pages-after.json"
python3 doc/probes/publication/github_probe.py check-public original
python3 - <<'PY'
import json, os
from pathlib import Path
p=Path(os.environ['PROBE_DIR'])
before=json.loads((p/'pages-before.json').read_text())
after=json.loads((p/'pages-after.json').read_text())
for k in ('build_type','source','cname','https_enforced','html_url'):
 assert before[k]==after[k], (k,before[k],after[k])
rule=json.loads((p/'main-policy-created.json').read_text())
assert rule['name']=='main' and rule['id']!=65003853
assert str(rule['id'])==os.environ['PROBE_MAIN_POLICY_ID']
PY
gh api --method DELETE "repos/$PROBE_REPO/environments/github-pages/deployment-branch-policies/$PROBE_MAIN_POLICY_ID"
gh api --method GET "repos/$PROBE_REPO/environments/github-pages/deployment-branch-policies" > "$PROBE_DIR/policies-after.json"
gh api --method GET "repos/$PROBE_REPO/git/ref/heads/gh-pages" > "$PROBE_DIR/branch-after.json"
python3 - <<'PY'
import json, os
from pathlib import Path
p=Path(os.environ['PROBE_DIR'])
assert json.loads((p/'policies-before.json').read_text())==json.loads((p/'policies-after.json').read_text())
assert json.loads((p/'branch-before.json').read_text())['object']['sha']==json.loads((p/'branch-after.json').read_text())['object']['sha']
PY
```

Jeśli sama zmiana źródła nie przywróci działającej publikacji gałęziowej,
sprawdzić `gh api --method GET repos/dlubom/jktz-mapa/actions/runs/41183308660`
(SHA oryginału, `head_branch=gh-pages`, dostępność Re-run), a następnie
`gh run rerun 41183308660 --repo dlubom/jktz-mapa`. Zaczekać na terminalny
sukces i ponowić `check-public original`. Ten fallback nadal wymaga
reguły `gh-pages`; nie zmienia treści tej gałęzi. Jeżeli GitHub nie
pozwala na Re-run, zatrzymać się z raportem, bez tworzenia nowego commitu
na `gh-pages` lub zastępowania obecnej strony niezweryfikowanym buildem.

## Kryteria zaliczenia i granice

Zaliczenie wymaga zapisanych ID runów/attempt/jobów i JSON z historią,
stanów przed/po, sum paczek i publicznych bajtów. Oczekiwane wyniki:
oba oczekujące runy zachowane w kolejce i zablokowane przez `pending`;
anulowane B odzyskane wyłącznie przez jego udany krok i publiczny marker;
drugi recover bez deployu/zapisu; rollback A z nowym okresem ochrony B;
stary B bez ponownej publikacji; finalny oryginał i ustawienia/reguły
zgodne ze stanem sprzed próby. Ochrona bieżącej paczki jest bezterminowa,
zastąpionej co najmniej 15 dni od potwierdzenia. Nieznany wynik blokuje
każdą nową publikację; żadna ścieżka nie usuwa archiwów.

To **nie test Latest**, importerów ani kompletnego workflow. Paczki są
z góry przypięte; nie ma artefaktu `inputs-<run_id>` trzech źródeł.
Dzisiejsza próba nie dowodzi faktycznego przechowania przez 120 dni,
kill wewnątrz POST, fizycznej utraty runnera, automatycznego odzysku unknown,
wszystkich awarii API/CAS ani bezpieczeństwa zmian administracyjnych
poza blokadą. Te luki pozostają jawne po pomyślnym A → B → A.

Źródła API i odczyty wersji: [PAGES_PUBLICATION_API_CHECK.md](../../PAGES_PUBLICATION_API_CHECK.md).
Przebieg zatwierdzonej próby i poprawka transportu:
[dziennik wykonania](../../PAGES_PUBLICATION_GITHUB_TRIAL.md).
