#!/bin/sh
set -e
# Read proxy secret from mounted file if available, substitute into nginx.conf
if [ -f /etc/rcars/proxy-verification-secret ]; then
    export PROXY_SECRET=$(cat /etc/rcars/proxy-verification-secret)
else
    export PROXY_SECRET=""
fi
envsubst '${PROXY_SECRET}' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf
exec nginx -c /tmp/nginx.conf -g 'daemon off;'
