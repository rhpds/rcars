#!/bin/sh
# Read proxy secret from mounted file if available, substitute into nginx.conf
if [ -f /etc/rcars/proxy-verification-secret ]; then
    export PROXY_SECRET=$(cat /etc/rcars/proxy-verification-secret)
else
    export PROXY_SECRET=""
fi
envsubst '${PROXY_SECRET}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
