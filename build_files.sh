#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Vercel pre-build script — runs collectstatic so WhiteNoise and Vercel CDN
# can serve the compressed, hash-named static files.
#
# Vercel invokes this script via the @vercel/static-build builder before the
# @vercel/python serverless function is packaged.
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

echo "── Installing Python dependencies ──────────────────────────────────────"
pip install -r api/requirements.txt

echo "── Collecting static files ──────────────────────────────────────────────"
# Generate a throw-away SECRET_KEY for this build invocation only.
# Django needs a valid key to import settings; the key is never used at runtime.
BUILD_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

DJANGO_SETTINGS_MODULE=gdgProject.settings.vercel \
  SECRET_KEY="${BUILD_SECRET_KEY}" \
  DATABASE_URL=sqlite:////tmp/build.db \
  python gdgProject/manage.py collectstatic --noinput --clear

echo "── Static files ready in gdgProject/staticfiles/ ───────────────────────"
