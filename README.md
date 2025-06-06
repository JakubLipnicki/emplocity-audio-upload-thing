# Emplocity Audio Upload Thing

Platforma umożliwiająca użytkownikom wysyłanie, udostępnianie, ocenianie i odkrywanie plików audio. Aplikacja integruje system płatności PayU (w trybie Sandbox) do zakupu dodatkowych elementów personalizacji profilu, takich jak ramki.

Repozytorium projektu: [https://github.com/JakubLipnicki/emplocity-audio-upload-thing](https://github.com/JakubLipnicki/emplocity-audio-upload-thing)

## Spis Treści

*   [Funkcjonalności](#funkcjonalności)
*   [Technologie](#technologie)
*   [Wymagania Wstępne](#wymagania-wstępne)
*   [Instalacja i Uruchomienie](#instalacja-i-uruchomienie)
*   [Dostęp do Usług](#dostęp-do-usług)
*   [Kluczowe Zmienne Środowiskowe](#kluczowe-zmienne-środowiskowe)
*   [Struktura Projektu](#struktura-projektu)
*   [Endpointy API (Przykładowe)](#endpointy-api-przykładowe)

## Funkcjonalności

*   **Uwierzytelnianie Użytkowników:**
    *   Rejestracja nowych użytkowników.
    *   Weryfikacja adresu email po rejestracji.
    *   Logowanie za pomocą emaila i hasła.
    *   System oparty na tokenach JWT (access i refresh tokeny przechowywane w ciasteczkach HttpOnly).
    *   Wylogowywanie.
    *   Mechanizm resetowania hasła.
*   **Zarządzanie Plikami Audio:**
    *   Wysyłanie (upload) plików audio przez użytkowników.
    *   Możliwość ustawienia tytułu, opisu, tagów oraz statusu publicznego/prywatnego dla audio.
    *   Przeglądanie listy najnowszych publicznych plików audio (z paginacją).
    *   Wyświetlanie szczegółów pojedynczego pliku audio.
    *   Usuwanie własnych plików audio.
    *   Pobieranie plików audio z przyjaznymi nazwami (np. `TytułUtworu.mp3` zamiast `uuid.mp3`) dzięki ustawieniu metadanych `Content-Disposition` w MinIO.
*   **Interakcje Społecznościowe:**
    *   System polubień (like/dislike) dla plików audio.
    *   Wyświetlanie liczby polubień/niepolubień dla audio.
    *   Przeglądanie plików audio polubionych przez użytkownika.
    *   System tagów: możliwość tagowania audio i przeglądania plików po tagach.
*   **Płatności (Integracja z PayU Sandbox):**
    *   Możliwość zakupu elementów personalizacji profilu (np. ramek profilowych).
    *   Inicjowanie płatności i przekierowanie do bramki PayU.
    *   Obsługa powiadomień zwrotnych (IPN) od PayU w celu aktualizacji statusu transakcji (weryfikacja podpisu).
    *   Automatyczne przyznawanie zakupionego elementu (np. aktualizacja pola w profilu użytkownika) po pomyślnej płatności.

## Technologie

*   **Backend:**
    *   Python 3.10
    *   Django 5.1.7
    *   Django REST Framework
    *   `djangorestframework-simplejwt` (dla autentykacji JWT)
    *   `psycopg2-binary` (adapter PostgreSQL)
    *   `python-decouple` (zarządzanie konfiguracją)
    *   `django-cors-headers` (obsługa CORS)
    *   `django-storages` i `boto3` (integracja z MinIO/S3)
    *   `requests` (komunikacja z API PayU)
*   **Frontend:**
    *   Nuxt.js (framework oparty na Vue.js)
    *   Tailwind CSS
    *   Shadcn UI (przez `shadcn-nuxt`)
*   **Baza Danych:** PostgreSQL (wersja 16 w Dockerze)
*   **Przechowywanie Plików:** MinIO (kompatybilne z S3, uruchamiane w Dockerze)
*   **Obsługa Płatności:** PayU (API REST, tryb Sandbox)
*   **Konteneryzacja:** Docker, Docker Compose
*   **Narzędzia Deweloperskie:**
    *   MailHog (testowanie emaili lokalnie, w Dockerze)
    *   `pip-tools` (zarządzanie zależnościami Python)
    *   `black`, `flake8`, `isort`, `mypy` (linting i formatowanie kodu)

## Wymagania Wstępne

Przed uruchomieniem projektu upewnij się, że masz zainstalowane:
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (zawiera Docker Engine i Docker Compose)
*   [Git](https://git-scm.com/downloads)

## Instalacja i Uruchomienie

1.  **Sklonuj repozytorium:**
    ```bash
    git clone https://github.com/JakubLipnicki/emplocity-audio-upload-thing.git
    cd emplocity-audio-upload-thing
    ```

2.  **Skonfiguruj zmienne środowiskowe:**
    *   W głównym katalogu projektu skopiuj plik `.env.example` (jeśli istnieje) do nowego pliku o nazwie `.env`:
        ```bash
        # Jeśli masz .env.example w repozytorium:
        # cp .env.example .env 
        ```
        Jeśli nie ma `.env.example`, utwórz plik `.env` ręcznie.
    *   Otwórz plik `.env` i uzupełnij wszystkie wymagane wartości. Zobacz sekcję [Kluczowe Zmienne Środowiskowe](#kluczowe-zmienne-środowiskowe) poniżej oraz plik `.env.example` (jeśli jest dostępny) jako przewodnik.
    *   **Szczególnie ważne:** Uzupełnij klucze dla PayU Sandbox (`PAYU_POS_ID_SANDBOX`, `PAYU_OAUTH_CLIENT_ID_SANDBOX`, `PAYU_OAUTH_CLIENT_SECRET_SANDBOX`, `PAYU_SIGNATURE_KEY_SANDBOX`), które znajdziesz w swoim panelu PayU Sandbox po skonfigurowaniu testowego sklepu.

3.  **Zbuduj i uruchom kontenery Docker:**
    W głównym katalogu projektu (tam gdzie jest `docker-compose.yml`):
    ```bash
    docker-compose build
    docker-compose up -d 
    ```
    Aby zobaczyć logi poszczególnych serwisów (np. `django`, `frontend`): `docker-compose logs -f django`
    Aby zatrzymać kontenery: `docker-compose down`

4.  **Zastosuj migracje bazy danych:**
    Poczekaj chwilę, aż kontener bazy danych (`db`) się w pełni uruchomi. Następnie wykonaj:
    ```bash
    docker-compose exec django python manage.py migrate
    ```
    *(Serwis Django w `docker-compose.yml` nazywa się `django`)*

5.  **Stwórz superużytkownika Django (do dostępu do panelu admina):**
    ```bash
    docker-compose exec django python manage.py createsuperuser
    ```
    Postępuj zgodnie z instrukcjami, aby ustawić email (jako nazwę użytkownika), hasło.

## Dostęp do Usług

Po pomyślnym uruchomieniu, usługi powinny być dostępne pod następującymi adresami (domyślnie):

*   **Backend API (Django):** `http://localhost:8000/api/`
*   **Panel Admina Django:** `http://localhost:8000/admin/`
*   **Frontend Aplikacji (Nuxt.js):** `http://localhost:3000/` (zgodnie z `FRONTEND_URL` w `.env`)
*   **MailHog (Interfejs Webowy do emaili):** `http://localhost:8025/`
*   **MinIO (Konsola Webowa do plików):** `http://localhost:9001/` (login/hasło z `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` z `.env`, które są zazwyczaj takie same jak `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`)
*   **PayU Sandbox Panel:** `https://merch-prod.snd.payu.com/`

## Kluczowe Zmienne Środowiskowe (plik `.env`)

Upewnij się, że plik `.env` w głównym katalogu projektu zawiera co najmniej następujące zmienne (zobacz plik `.env.example` jako pełniejszy przewodnik):

*   `SECRET_KEY`: Klucz sekretny Django.
*   `DEBUG`: `True` dla developmentu.
*   `ALLOWED_HOSTS`: Np. `localhost,127.0.0.1`. Dla testów PayU z `ngrok`, dodaj tutaj swój adres ngrok.
*   `BASE_URL`: Główny URL Twojego backendu (np. `http://localhost:8000`). Zmień na URL ngrok podczas testowania powiadomień PayU.
*   `FRONTEND_URL`: Główny URL Twojego frontendu (np. `http://localhost:3000`).
*   `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Dane dostępowe do PostgreSQL.
*   `EMAIL_HOST=mailhog`, `EMAIL_PORT=1025` (dla MailHog).
*   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: Dane dostępowe do MinIO (dla `MINIO_ROOT_USER` i `MINIO_ROOT_PASSWORD`).
*   `PAYU_SANDBOX_MODE=True`
*   `PAYU_POS_ID_SANDBOX`, `PAYU_OAUTH_CLIENT_ID_SANDBOX`, `PAYU_OAUTH_CLIENT_SECRET_SANDBOX`, `PAYU_SIGNATURE_KEY_SANDBOX`: Klucze dla PayU Sandbox.

## Struktura Projektu

*   **`.env`**: Plik konfiguracyjny ze zmiennymi środowiskowymi (ignorowany przez Git).
*   **`.env.example`**: Szablon pliku `.env` (dodawany do Git).
*   **`backend/`**: Zawiera kod aplikacji Django (Python).
    *   **`accounts/`**: Zarządzanie użytkownikami, autentykacja JWT.
    *   **`audio/`**: Zarządzanie plikami audio, tagami, polubieniami.
    *   **`payments/`**: Integracja z systemem płatności PayU.
    *   **`project/`**: Główny katalog konfiguracyjny projektu Django (`settings.py`, `urls.py`).
    *   **`requirements/`**: Pliki `requirements.in` i `requirements.txt` dla zależności Python.
    *   `manage.py`: Skrypt narzędziowy Django.
    *   `Dockerfile`: Instrukcje budowania obrazu Docker dla backendu.
*   **`frontend/`**: Zawiera kod aplikacji frontendowej napisanej w Nuxt.js (Vue.js).
    *   `Dockerfile`: Instrukcje budowania obrazu Docker dla frontendu.
    *   `package.json`: Zależności i skrypty Node.js dla frontendu.
    *   `nuxt.config.ts`: Główny plik konfiguracyjny Nuxt.js.
*   **`docker-compose.yml`**: Definicja i konfiguracja wszystkich serwisów Docker.

## Endpointy API (Przykładowe)

*   **Konta (`/api/`):**
    *   `POST /api/register` - Rejestracja.
    *   `POST /api/login` - Logowanie.
    *   `GET /api/user` - Dane zalogowanego użytkownika.
    *   `POST /api/logout` - Wylogowanie.
    *   `GET /api/verify-email/?token=<token>` - Weryfikacja emaila.
*   **Audio (`/api/audio/`):**
    *   `POST /api/audio/upload/` - Wysyłanie pliku audio.
    *   `GET /api/audio/latest/` - Najnowsze publiczne audio.
    *   `GET /api/audio/<uuid>/` - Szczegóły audio.
    *   `POST /api/audio/<uuid>/like/` - Polubienie/Niepolubienie audio.
*   **Płatności (`/api/payments/`):**
    *   `POST /api/payments/initiate/` - Inicjowanie płatności PayU. (Ciało JSON: `{"amount": <int:grosze>, "description": "<str>"}`)
    *   `POST /api/payments/notify/callback/` - Endpoint dla IPN od PayU.
    *   `GET /api/payments/finish/` - Strona powrotu po płatności.

---