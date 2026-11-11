#!/bin/bash

echo "==> Ensuring staticfiles directories exist..."
mkdir -p staticfiles/static
mkdir -p staticfiles/css
mkdir -p staticfiles/js

# Populate static assets in both root and /static prefix
cp -r static/* staticfiles/ 2>/dev/null || true
cp -r static/* staticfiles/static/ 2>/dev/null || true
cp static/favicon.ico staticfiles/favicon.ico 2>/dev/null || true
cp static/favicon.svg staticfiles/favicon.svg 2>/dev/null || true

echo "==> Installing Python dependencies..."
python3 -m pip install -r requirements.txt --break-system-packages || python3 -m pip install -r requirements.txt || true

echo "==> Collecting static assets..."
python3 manage.py collectstatic --noinput --clear || true

# Re-copy custom static files to guarantee presence
cp -r static/* staticfiles/ 2>/dev/null || true
cp -r static/* staticfiles/static/ 2>/dev/null || true
cp static/favicon.ico staticfiles/favicon.ico 2>/dev/null || true
cp static/favicon.svg staticfiles/favicon.svg 2>/dev/null || true

echo "==> Build completed successfully!"
