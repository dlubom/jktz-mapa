# Wyszukiwanie i wybór podkładu

> Realizacja: równoległe, niezależne zadania z integracją i przeglądem całej zmiany.

**Cel:** znaleźć lokalizację jaskini i dostępne materiały oraz wiedzieć, jaki podkład faktycznie widać.

**Architektura:** wspólny ranking jaskiń i otworów oraz osobny kontroler dostępnego wyszukiwania. Metadane podkładów i czysta funkcja statusu są oddzielone od zdarzeń OpenLayers. Widok korzysta z jednego wyboru i statusu w panelu warstw oraz przy planie.

**Zakres:** TypeScript, OpenLayers, dotychczasowe pełne dane. Zachowujemy EPSG:2180, współrzędne, niepewności, diagnostykę i obsługę planów. Relacje tylko po jawnych ID; `sourceCaveId` planu nie jest identyfikatorem GPS jaskini.

## Przyjęte decyzje

- Jedna lista wyników, wspólna ocena: dokładne ID, dokładna nazwa, początek nazwy, fragment nazwy, słowa w nazwie, metadane. Typ rekordu nie podnosi trafności.
- Wynik opisuje typ (jaskinia lub otwór), ID i jawnie powiązane plany/ciągi. Materiały jaskini wynikają z jej `objectIds` i relacji tych obiektów.
- Strzałki wybierają wynik bez zmiany tekstu; granice nie zawijają. Enter otwiera wybrany lub pierwszy wynik otwartej listy. Escape zamyka listę; fokus pozostaje w wyszukiwarce. Zamknięte wyniki nie reagują na Enter.
- Nazwy podkładów opisują treść, zachowując rok, dostawcę i wariant. Legenda geologii jest dostępna także przy planie.
- Wybór podkładu pozostaje zachowany przy skali, braku pokrycia lub błędach. Osobny komunikat opisuje bieżący obraz, ładowanie i OSM w tle; brak kafla nie dowodzi awarii całej usługi.
- Nie wnioskujemy zasięgu TPN z nazw jaskiń ani samego błędu pobrania. Używamy udokumentowanego zasięgu tam, gdzie istnieje.

## Plan odbioru

- Ranking i relacje: testy dokładnego ID/nazwy, mieszanych typów, metadanych, polskich znaków oraz braku relacji na podstawie nazw.
- Wyszukiwanie: testy przeglądarkowe strzałek, Enter, Escape, aktywnego wyniku, pustej listy i ARIA.
- Podkłady: testy skali, znanego zasięgu, częściowego pokrycia, ładowania, błędów, odzyskania i krycia; synchronizacja obu kontrolek i legendy.
- Regresje: `npm test`, Python, build i Chromium/Firefox/WebKit, duży/mały/niski ekran; działający cały plan i detal, rzeczywiste usługi.
- Niezależny przegląd, poprawki, commit na historii gałęzi PR #11 i zielony `map` dla tego commita.
- Workflow `Preview selected PR` dla PR #11: zielone resolve/build/publish, publiczny manifest zgodny z PR, sprawdzona mapa i plan; adres na początku opisu PR.

## Szczególna uwaga w przeglądzie

- Dokładna jaskinia musi wyprzedzić otwór zawierający tylko wzmiankę w metadanych.
- Brak jawnej relacji nie może dawać obietnicy planu lub ciągu.
- Zamknięta lista i poprzednie wyniki nie mogą otwierać przypadkowego rekordu.
- Odpowiedzi poprzedniego źródła i błędy poza widokiem nie mogą zmieniać bieżącego statusu.
- Ładowanie, zerowe krycie i wyjście poza zasięg nie mogą przedstawiać niewidocznego podkładu jako widocznego.
