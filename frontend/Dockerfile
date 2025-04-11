# Wybór obrazu bazowego
FROM node:20

# Ustawienie katalogu roboczego na /app
WORKDIR /app

# Kopiowanie package.json i package-lock.json
COPY package*.json /app/

# Instalowanie zależności
RUN npm install

# Kopiowanie całego katalogu frontend do katalogu /app
COPY . /app/

# Budowanie aplikacji frontendowej
RUN npm run build

# Uruchamianie aplikacji w trybie produkcyjnym przy użyciu npx (bez instalacji globalnej)
CMD ["node", "./server/index.mjs"]