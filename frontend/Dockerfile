# Choosing the base image
FROM node:20

# Setting the working directory to /app
WORKDIR /app

# Copying package.json and package-lock.json
COPY package*.json /app/

# Installing dependencies
RUN npm install

# Copying the entire frontend directory to the /app directory
COPY . /app/

# Building the frontend application
RUN npm run build

# Running the application in production mode using npx (without global installation)
CMD ["node", "./server/index.mjs"]
