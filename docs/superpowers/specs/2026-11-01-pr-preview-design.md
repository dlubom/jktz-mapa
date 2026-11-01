# Podgląd PR i kompletna paczka mapy

Uzgodnione: każdy PR otrzymuje kompletny ZIP, a wybrany PR jest publikowany pod osobnym adresem GitHub Pages `https://dlubom.github.io/jktz-mapa-preview/`. Produkcja zachowuje ręczną publikację i osobną ewidencję. Zmiany aplikacji przechodzą przez PR; wyjątek wymaga wyraźnego polecenia użytkownika.

## Podejścia

Sam ZIP byłby prostszy, ale utrudnia testy na telefonie. Kopie wszystkich PR pod jedną stroną szybko wykorzystałyby limit 1 GB. Wybrano ZIP dla każdego PR i jedną stronę dla wskazanego PR.

## Wykonanie

CI źródła udostępnia pliki gotowej mapy bez zagnieżdżonego archiwum, ze skryptem `serve.py`, instrukcją, przypięciami danych, sumami i identyfikacją kandydata scalenia. ZIP wymaga Python 3 do lokalnego serwera; podkłady zewnętrzne wymagają internetu.

Osobne repozytorium podglądu ma ręczny workflow z numerem PR. Zaufany etap rozpoznaje aktualny otwarty PR do main i przypina head/base/merge SHA. Etap budowy wykonuje kod tego PR bez sekretów i z uprawnieniami tylko do odczytu, uruchamia pełne testy oraz przygotowuje artefakt. Osobny etap publikacji wykonuje wyłącznie kod repozytorium podglądu, weryfikuje paczkę i aktualność PR, po czym publikuje przez OIDC. Nie są potrzebne dodatkowe tokeny ani klucze. Jedna kolejka obejmuje cały workflow, aby starsza budowa nie nadpisała nowszego wyboru. Strona pokazuje numer PR i commit. Nieudana budowa pozostawia poprzedni podgląd.

Konfiguracja repozytorium podglądu jest przechowywana w tym projekcie jako szablon; aktualizacje istniejących gałęzi main idą przez PR. Inicjalizacja nowego repozytorium tworzy jego pierwszy commit, następnie main otrzymuje ochronę.

## Odbiór

Sprawdzić kompletność paczki i sumy, lokalne HTTP bez Node/GDAL, odrzucenie niebezpiecznych ścieżek i symlinków, otwarty PR i zgodność wszystkich SHA, oddzielne uprawnienia budowy/publikacji, publiczny manifest oraz mapę pod ścieżką podglądu. Fizyczny telefon pozostaje odbiorem użytkownika.
