# Aktualność ciągów pomiarowych po publikacji

## Problem

Po publikacji JKTZ v1.4.15 laptop z wcześniej otwartą mapą nadal pokazywał starsze dane po zwykłym odświeżeniu, podczas gdy na telefonie poprawki były widoczne. GitHub Pages zwraca `Cache-Control: max-age=600` dla `data/catalog.json` i plików ciągów. Mapa pobiera te zasoby osobno przez `fetch` z domyślnym trybem cache. Katalog i geometria mogą więc pochodzić z różnych publikacji. Trafienie w CDN potwierdzono dla `data/models/LodowaMalolacka.geojson`. Dokładne źródło odpowiedzi na laptopie pozostaje nieustalone.

## Propozycja

1. Przy uruchomieniu mapy pobierać `data/catalog.json` z `cache: 'no-cache'`, aby przeglądarka sprawdzała aktualność zapisanej odpowiedzi. Sprawdzić działanie tej rewalidacji również na GitHub Pages, gdzie odpowiedź może pochodzić z CDN.
2. W `scripts/pipeline.py` nadawać każdemu plikowi ciągu nazwę `data/models/<id>.<sha256>.geojson` na podstawie końcowych bajtów GeoJSON. Zapisać tę ścieżkę w istniejącym polu `models[].url`. Identyfikatory ciągów, powiązania i odnośniki do obiektów pozostają stałe.
3. Pakować katalog i wskazywane pliki jako jedną migawkę. Sprawdzać w CI, czy wszystkie ścieżki ciągów z katalogu istnieją w gotowym `dist/` oraz czy hash w nazwie odpowiada zawartości. Rollback publikuje katalog i pliki z tej samej paczki.
4. Uwzględnić kartę otwartą podczas wdrożenia. Gdy leniwie ładowany ciąg zwróci `404`, sprawdzić katalog ponownie. Jeżeli dostępna jest inna migawka, pokazać komunikat z przyciskiem odświeżenia mapy. Zachować zwykłą obsługę błędów dla pozostałych przypadków.

Wersjonowanie dotyczy plików ciągów. Ten sam GeoJSON zachowuje adres, więc przeglądarka może nadal korzystać z zapisanej kopii. Plany i podkłady są poza zakresem.

## Rozważone podejścia

- Sama rewalidacja katalogu i GeoJSON jest prostsza, ale każde żądanie ciągu wymaga sprawdzenia aktualności. Stały URL wciąż pozwala połączyć katalog i geometrię z dwóch publikacji.
- Parametr `?v=…` rozdziela wpisy w cache przeglądarki. W obserwacji na GitHub Pages nowy parametr nadal dał `X-Cache: HIT` dla tego samego pliku, więc proponowane rozwiązanie wersjonuje fizyczną ścieżkę.

## Kryteria odbioru

- Dwa buildy z tą samą treścią ciągu generują ten sam URL. Zmiana geometrii pod tym samym ID daje nowy URL. Każdy URL w katalogu wskazuje istniejący plik z pasującą sumą.
- Po przejściu z paczki A na B zwykłe odświeżenie w tym samym profilu, który pobrał katalog i ciąg z A, pokazuje wersję B w „Źródłach” oraz geometrię B. Test obejmuje zarówno rozgrzany cache przeglądarki, jak i publikację na GitHub Pages w repozytorium podglądu. Porównać pobrane bajty ciągu, nie samą etykietę wydania.
- Po zmianie paczki sprawdzić otwartą kartę, która dopiero teraz żąda ciągu z A. Po rollbacku sprawdzić w tym samym profilu wersję katalogu i geometrię przywróconej paczki, także dla paczki utworzonej przed zmianą formatu ścieżek.
