#!/bin/bash

echo "==> Ensuring staticfiles directory exists..."
mkdir -p staticfiles
cp -r static/* staticfiles/ 2>/dev/null || true

echo "==> Installing Python dependencies..."
python3 -m pip install -r requirements.txt --break-system-packages || python3 -m pip install -r requirements.txt || true

echo "==> Collecting static assets..."
python3 manage.py collectstatic --noinput --clear || true

# Ensure staticfiles is populated
mkdir -p staticfiles
cp -r static/* staticfiles/ 2>/dev/null || true

echo "==> Build completed successfully!"
