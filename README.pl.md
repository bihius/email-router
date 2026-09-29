# email-router

[![CI](https://github.com/bihius/email-router/actions/workflows/ci.yml/badge.svg)](https://github.com/bihius/email-router/actions/workflows/ci.yml)

[English version](README.md)

PoC routera wiadomości opartego na AI. Serwis FastAPI przekazuje wiadomość agentowi LangChain, który korzysta z lokalnego modelu w Ollamie. Agent wybiera dział i wywołuje narzędzie `send_email`, a MailHog przechwytuje wysłany e-mail.

Projekt zawiera też eksperyment: tę samą decyzję podejmuje [Laya](https://huggingface.co/convaiinnovations/laya), lokalny model decyzyjny typu System One, zamiast LLM. Na 100 polskich i 100 angielskich zgłoszeniach testowych był ponad 200 razy szybszy od domyślnego agenta, ale dużo mniej trafny, dlatego domyślnie jest wyłączony (zob. [Eksperyment: silnik System One](#eksperyment-silnik-system-one-laya) i [`eval/`](eval/README.md)).

## Uruchomienie

```bash
cp .env.example .env   # opcjonalne: tylko gdy chcesz zmienić ustawienia domyślne
docker compose up -d
```

Przy pierwszym starcie kontener `ollama-pull` pobiera model (`qwen3:8b`, ok. 5,2 GB). API czeka na koniec pobierania, a jego kontener zgłasza stan `healthy`, gdy przyjmuje zapytania (`docker compose up -d --wait` czeka do tego momentu). Na CPU pierwsze zapytanie dodatkowo ładuje model do pamięci; na Apple M4 trwało to prawie 3 minuty, a kolejne, dopóki model jest w pamięci, zajmują ok. 50 s, przy wyłączonym rozumowaniu ok. 6,5 s (zob. [Decyzje architektoniczne](#decyzje-architektoniczne)).

| Usługa | Adres |
| --- | --- |
| Dokumentacja API (Swagger) | <http://localhost:8000/api/v1/docs> |
| Panel MailHog | <http://localhost:8025> |

## Przykładowe zapytanie

```bash
curl -sS -X POST http://localhost:8000/api/v1/route \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "jan.nowak@example.com",
    "message": "Nie działa mi komputer"
  }'
```

```json
{"status": "sent", "department": "it", "to": "it@example.com", "engine": "ollama", "probability": null}
```

W MailHogu wiadomość ma `To: it@example.com` i `Reply-To: jan.nowak@example.com`. Jeśli model nie wykona poprawnego wywołania narzędzia, mail nie zostaje wysłany, a API zwraca `502`.

## Eksperyment: silnik System One (Laya)

Kierowanie zgłoszenia to klasyfikacja: wybór jednej z pięciu znanych opcji. LLM robi to, generując wywołanie narzędzia token po tokenie. Modele System One, nowa klasa modeli zaprezentowana przez TypeSafe AI razem z modelem [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), odpowiadają na pytanie o określonym typie, np. „która z tych opcji?”, w jednym przebiegu modelu. Zwracają prawdopodobieństwo dla każdej opcji i nie generują tekstu. To dobrze pasuje do routingu, więc projekt sprawdza to podejście. Jev działa jako usługa w chmurze, a zadanie wymaga interpretacji wiadomości przez model lokalny. Dlatego eksperyment używa modelu [Laya](https://huggingface.co/convaiinnovations/laya): to otwarty (Apache-2.0) model System One, który działa lokalnie i udostępnia API zgodne z Jevem.

Zadanie tego nie wymaga, a domyślny silnik od tego nie zależy. Żeby wypróbować, wystarczy zmienić jedną linię w `.env`:

```bash
cp .env.example .env
# w .env: ROUTER_ENGINE=laya
docker compose up -d
```

`COMPOSE_PROFILES=${ROUTER_ENGINE}` w `.env` uruchamia kontener `laya`. Jest on budowany z `laya-serve/Dockerfile` (PyTorch na CPU, ok. 1,5 GB) i pobiera checkpoint `laya-multilingual` (ok. 650 MB) do wolumenu. API czeka, aż model się załaduje. Ollama nadal startuje, bo wymaga jej zadanie. Odpowiedź API zawiera wtedy `"engine": "laya"` oraz prawdopodobieństwo, jakie Laya przypisała wybranemu działowi. W tym trybie nie ma wywołania narzędzia: jego argument zastępuje odpowiedź modelu Laya, a mail wysyła ten sam kod.

**Wynik: dużo szybciej, ale jakość spadła za bardzo.** Pomiar na 100 zgłoszeniach, każde po polsku i po angielsku o tej samej treści ([`eval/`](eval/README.md), CPU, Apple M4, pełna ścieżka przez API łącznie z SMTP):

| Silnik | PL | EN | Mediana czasu |
| --- | --- | --- | --- |
| Agent Ollama `qwen3:8b`, z rozumowaniem (domyślny) | 94/100 | 94/100 | 46–51 s |
| Agent Ollama `qwen3:8b`, bez rozumowania (`OLLAMA_THINK=false`) | 91/100 | 93/100 | 6,2–6,5 s |
| Laya `laya-multilingual` | 56/100 | 65/100 | 0,19 s |

Laya jest ok. 250 razy szybsza od domyślnego agenta i ponad 30 razy szybsza od agenta bez rozumowania, ale bez douczenia kieruje 44 ze 100 polskich zgłoszeń do złego działu, dlatego domyślnym silnikiem zostaje agent. Język tłumaczy tylko część tej różnicy. Laya prawie nigdy nie wybiera działu `other` (opcja „wszystko inne”) i często myli `help_desk` z `it`, czyli najmniej wyraźną granicę na liście działów z zadania. Zmiana opisów działów, wybór innego checkpointu, próg prawdopodobieństwa ani kaskada „najpierw Laya, potem agent” nie zniwelowały różnicy ([`eval/README.md`](eval/README.md)). Pozostaje douczenie (fine-tuning) Lai na oznaczonych zgłoszeniach z danej dziedziny, co wykracza poza ten PoC.

Dla porównania te same zgłoszenia wysłano jednorazowo do modelu Jev, czyli modelu System One od TypeSafe, działającego w chmurze. Uzyskał 96/100 (PL) i 94/100 (EN), czyli mniej więcej tyle samo co agent z `qwen3:8b` (94/100 w obu językach z rozumowaniem, 91/100 i 93/100 bez niego), więc na tym zbiorze trafność nie rozróżnia obu podejść. Różnią je szybkość i pewność odpowiedzi. Jev odpowiada w ok. 0,25 s, mniej więcej 25 razy szybciej niż agent bez rozumowania i 200 razy szybciej niż z nim, a jego prawdopodobieństwo wiarygodnie wskazuje odpowiedzi, które mogą być błędne. Oba silniki mylą się też zwykle na innych zgłoszeniach: gdyby brać odpowiedź Jeva, gdy jego prawdopodobieństwo wynosi co najmniej 0,95, a w pozostałych przypadkach odpowiedź agenta, wynik wyniósłby 97/100 (PL) i 96/100 (EN), a do wolnego modelu trafiałoby tylko ok. co piąte zgłoszenie. Z agentem bez rozumowania takie połączenie daje 97/100 i 95/100 przy średnio ok. 2 s na zgłoszenie. To wyliczenie na zapisanych wynikach, a nie zaimplementowane rozwiązanie. Projekt nie korzysta z Jeva, bo zadanie wymaga modelu lokalnego, a otwarty model System One działający lokalnie nie jest jeszcze wystarczająco dobry. Pomiar jest opisany w [`eval/README.md`](eval/README.md#reference-typesafe-jev-hosted-not-part-of-the-project).

Szczegółowe wyniki eksperymentu (`eval/README.md`) są po angielsku.

## Decyzje architektoniczne

- **Jedno narzędzie z ograniczonym argumentem.** Agent ma jedno narzędzie `send_email(department)`. Schemat argumentu to `Literal` z nazwami działów z katalogu. Jeśli model poda nazwę spoza katalogu, walidacja ją odrzuca, a agent przekazuje modelowi błąd, żeby mógł spróbować ponownie. Liczba kroków agenta jest ograniczona i na jedno zapytanie wychodzi najwyżej jeden mail. Jeśli model po wysłaniu maila dalej wywołuje narzędzie, zapytanie i tak kończy się sukcesem.
- **Routing tylko przez ustrukturyzowaną decyzję.** Aplikacja nigdy nie wyciąga nazwy działu z dowolnego tekstu wygenerowanego przez model. W przypadku Ollamy decyzją jest wywołanie narzędzia: bez wywołania nie ma maila. W przypadku Lai jest to odpowiedź typu `choice`, która może być tylko jedną z nazw z katalogu. Mail w obu przypadkach wysyła ten sam kod.
- **Model wybiera, kod adresuje maila.** Model widzi nazwy i opisy działów, ale nigdy adresów. `To` pochodzi z katalogu, `Reply-To` to nadawca z zapytania, a treścią jest oryginalna wiadomość.
- **Katalog działów w `data/departments.csv`** (`name`, `email`, `description`). Oba silniki biorą z niego listę opcji, więc nowy dział to jeden nowy wiersz. Plik musi zawierać wiersz `other` jako fallback. Opisy działów to krótkie listy angielskich słów kluczowych. Spośród trzech wariantów opisów porównanych na Lai w [`eval/`](eval/README.md) ten dał najlepszy wynik.
- **Model dostaje oczyszczony tekst, mail zawiera oryginał.** Zanim wiadomość trafi do któregokolwiek silnika, adresy data URI i długie ciągi base64 (np. obrazki wklejone w stopkę maila) są zastępowane przez `[attachment omitted]`, a wszystko po linii separatora podpisu (`-- ` lub `--`) jest usuwane. Jeden osadzony obrazek może być większy niż kontekst 2048 tokenów, a podpis dodaje słowa, które tylko przeszkadzają w klasyfikacji. Przekazywany mail zawiera pełną, oryginalną wiadomość.
- **Gotowość po `docker compose up -d`.** Jednorazowy kontener `ollama-pull` pobiera wagi modelu, a API startuje dopiero po jego udanym zakończeniu (a przy włączonej Lai także po tym, jak Laya zgłosi gotowość). Ollama, Laya i SMTP są dostępne tylko w sieci Compose. Na zewnątrz wystawione są tylko API i panel MailHoga. Wersje obrazów i zależności Pythona są przypięte.
- **Model `qwen3:8b`, temperatura 0, kontekst 2048.** Obsługuje wywołania narzędzi w Ollamie i kieruje poprawnie 94 ze 100 zgłoszeń testowych w obu językach. Ceną jest czas. qwen3 przed odpowiedzią rozumuje (tak działa domyślnie w Ollamie), więc na CPU jedno zgłoszenie zajmuje ok. 50 s, a pierwsze zapytanie, które dodatkowo ładuje model, trwało prawie 3 minuty. Dlatego domyślny timeout Ollamy to 300 s. Rozumowanie jest domyślnie włączone, bo dało najlepszy wynik, ale zysk jest niewielki: z `OLLAMA_THINK=false` w `.env` zgłoszenie zajmuje ok. 6,5 s, a agent trafił 91/100 (PL) i 93/100 (EN). Przy 100 zgłoszeniach na język ta różnica nie jest rozstrzygająca. Silnik, model, rozumowanie, timeout, rozmiar kontekstu i poziom logowania można zmienić w `.env` (zob. `.env.example`).

## Testy

```bash
pip install -r requirements.txt
python -m unittest discover -s tests
```

Testy zastępują Ollamę modelem ze skryptowanymi odpowiedziami, Layę zamockowaną odpowiedzią HTTP, a SMTP mockiem, więc nie wymagają uruchomionych kontenerów.
