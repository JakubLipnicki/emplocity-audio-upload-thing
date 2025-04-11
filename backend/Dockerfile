# Wybór obrazu bazowego
FROM python:3.10-slim

# Ustawienie katalogu roboczego na /app
WORKDIR /app

# Kopiowanie pliku requirements.txt do katalogu /app
COPY ./requirements/requirements.txt /app/

# Instalowanie zależności
RUN pip install --no-cache-dir -r /app/requirements.txt

# Kopiowanie wszystkich plików z katalogu backend do katalogu /app w kontenerze
COPY . /app/

# Zmienna środowiskowa dla Django
ENV PYTHONUNBUFFERED 1

# Uruchamianie aplikacji Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
