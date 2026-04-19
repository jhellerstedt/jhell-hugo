#!/bin/sh
set -e
export NODE_ENV="${NODE_ENV:-production}"
node /app/markdown-server/server.mjs &
exec nginx -g "daemon off;"
