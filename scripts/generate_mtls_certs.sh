#!/usr/bin/env bash
# Generate a private CA + server/client certificates for backend ↔ Ollama mTLS.
#
# Output (gitignored under certs/mtls/):
#   ca.crt / ca.key
#   server.crt / server.key   (presented by ollama-proxy)
#   client.crt / client.key   (presented by the portal backend)
#
# Usage:
#   ./scripts/generate_mtls_certs.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/certs/mtls"
mkdir -p "$OUT"

if ! command -v openssl >/dev/null 2>&1; then
  echo "ERROR: openssl is required." >&2
  exit 1
fi

if [ -f "$OUT/ca.crt" ] && [ -f "$OUT/client.crt" ] && [ -f "$OUT/server.crt" ]; then
  echo "mTLS certs already exist in $OUT — delete them first to regenerate."
  exit 0
fi

openssl genrsa -out "$OUT/ca.key" 4096
openssl req -x509 -new -nodes -key "$OUT/ca.key" -sha256 -days 3650 \
  -out "$OUT/ca.crt" \
  -subj "/C=IN/ST=Delhi/L=Delhi/O=IIITD ECE Portal/CN=ECE Portal mTLS CA"

openssl genrsa -out "$OUT/server.key" 2048
openssl req -new -key "$OUT/server.key" -out "$OUT/server.csr" \
  -subj "/C=IN/ST=Delhi/L=Delhi/O=IIITD ECE Portal/CN=ollama-proxy"
cat > "$OUT/server.ext" <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ollama-proxy
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF
openssl x509 -req -in "$OUT/server.csr" -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" \
  -CAcreateserial -out "$OUT/server.crt" -days 825 -sha256 -extfile "$OUT/server.ext"

openssl genrsa -out "$OUT/client.key" 2048
openssl req -new -key "$OUT/client.key" -out "$OUT/client.csr" \
  -subj "/C=IN/ST=Delhi/L=Delhi/O=IIITD ECE Portal/CN=ece-portal-backend"
cat > "$OUT/client.ext" <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF
openssl x509 -req -in "$OUT/client.csr" -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" \
  -CAcreateserial -out "$OUT/client.crt" -days 825 -sha256 -extfile "$OUT/client.ext"

rm -f "$OUT"/*.csr "$OUT"/*.ext "$OUT"/*.srl
chmod 600 "$OUT"/*.key
chmod 644 "$OUT"/*.crt

echo "Wrote mTLS materials to $OUT"
echo "  ca.crt, server.crt/key, client.crt/key"
echo "Next: docker compose -f docker-compose.ollama.yml up -d"
