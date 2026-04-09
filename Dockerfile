# Hugo Extended (SCSS) build → static files served by nginx.
# Clone with submodules: git clone --recurse-submodules …
# then: docker compose build && docker compose up -d

FROM peaceiris/hugo:v0.146.4 AS hugo

USER root
WORKDIR /src
COPY . .

RUN hugo --minify --environment production

FROM nginx:1.27-alpine

COPY --from=hugo /src/public /usr/share/nginx/html

EXPOSE 80
