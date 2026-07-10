#!/usr/bin/env bash
# Generate a self-signed TLS certificate for the ECE Portal (network/testing use).
#
# Produces ./certs/fullchain.pem and ./certs/privkey.pem which nginx.ssl.conf
# expects. For a public/production deployment, replace these with a certificate
# from your institute CA or Let's Encrypt instead of a self-signed one.
#
# Usage:
#   ./scripts/generate_self_signed_cert.sh [COMMON_NAME]
#   COMMON_NAME defaults to the machine's hostname; pass the server IP or domain
#   that users will type in the browser (e.g. 10.1.2.3 or ece.iiitd.ac.in).
set -euo pipefail

CN="${1:-$(hostname)}"
OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/certs"
mkdir -p "$OUT_DIR"

openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
  -keyout "$OUT_DIR/privkey.pem" \
  -out "$OUT_DIR/fullchain.pem" \
  -subj "/C=IN/ST=Delhi/L=Delhi/O=IIITD ECE/CN=${CN}" \
  -addext "subjectAltName=DNS:${CN},IP:127.0.0.1"

echo "Wrote $OUT_DIR/fullchain.pem and $OUT_DIR/privkey.pem (CN=${CN})"
echo "Next: mount ./certs into the frontend container and switch to nginx.ssl.conf (see frontend/nginx.ssl.conf header)."
