FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

ARG BACKEND_INTERNAL_URL=http://api:7777
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}

RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
