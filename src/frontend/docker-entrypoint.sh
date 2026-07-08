#!/bin/sh
set -e
# PROXY_SECRET is injected as an env var from the K8s Secret by the deployment manifest.
# Substitute it into the nginx config template and start nginx.
envsubst '${PROXY_SECRET}' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf
exec nginx -c /tmp/nginx.conf -g 'daemon off;'
