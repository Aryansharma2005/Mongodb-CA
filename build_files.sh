#!/bin/bash

echo "==> Installing Python dependencies..."
python3 -m pip install -r requirements.txt

echo "==> Collecting static assets..."
python3 manage.py collectstatic --noinput --clear

echo "==> Running database migrations..."
python3 manage.py migrate --noinput

echo "==> Build completed successfully!"
