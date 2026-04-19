# Hugo Extended (SCSS) build → static files served by nginx.
# Clone with submodules: git clone --recurse-submodules …
# then: docker compose build && docker compose up -d

FROM peaceiris/hugo:v0.146.4 AS hugo

USER root
WORKDIR /src
COPY . .

RUN hugo --minify --environment production

FROM node:22-alpine AS markdown-deps
WORKDIR /md
COPY docker/markdown-server/package.json ./
RUN npm install --omit=dev

FROM nginx:1.27-alpine

RUN apk add --no-cache nodejs

COPY --from=markdown-deps /md/node_modules /app/markdown-server/node_modules
COPY docker/markdown-server/server.mjs /app/markdown-server/server.mjs
COPY docker/entrypoint.sh /docker-entrypoint-markdown.sh
RUN chmod +x /docker-entrypoint-markdown.sh

COPY docker/nginx-default.conf /etc/nginx/conf.d/default.conf
COPY --from=hugo /src/public /usr/share/nginx/html

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint-markdown.sh"]
