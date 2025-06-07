FROM node:20-alpine

WORKDIR /app

# Chỉ cài đặt nếu cần build native modules
# RUN apk add --no-cache python3 make g++

RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --shamefully-hoist

COPY . .

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm build

EXPOSE 3000

CMD ["pnpm", "start"]