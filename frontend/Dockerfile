FROM node:20-alpine AS base

WORKDIR /app

COPY package.json ./

RUN npm install

COPY . .

RUN npm run build || true

EXPOSE 3000

CMD ["npm", "run", "dev"]
