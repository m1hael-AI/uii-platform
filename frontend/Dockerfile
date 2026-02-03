# Dockerfile для AI University Frontend
# Используется при деплое через docker-compose

FROM node:20-alpine

WORKDIR /app

# Копируем package files
COPY package*.json ./

# Устанавливаем зависимости
RUN npm ci

# Копируем исходный код
COPY . .

# Аргументы сборки (Build Args)
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_TELEGRAM_BOT_USERNAME

# Делаем их доступными как ENV во время сборки
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=$NEXT_PUBLIC_TELEGRAM_BOT_USERNAME

# Собираем приложение
RUN npm run build

# Открываем порт
EXPOSE 3000

# Запускаем production сервер
CMD ["npm", "start"]
