# Generate a private CA + server/client certificates for backend ↔ Ollama mTLS.
# Output: certs/mtls/{ca,server,client}.{crt,key}
#
# Usage (PowerShell):
#   .\scripts\generate_mtls_certs.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Out = Join-Path $Root "certs\mtls"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

if (-not (Get-Command openssl -ErrorAction SilentlyContinue)) {
    $gitOpenssl = "C:\Program Files\Git\usr\bin\openssl.exe"
    if (Test-Path $gitOpenssl) {
        $env:Path = "C:\Program Files\Git\usr\bin;" + $env:Path
    } else {
        Write-Error "openssl is required. Install OpenSSL or use Git Bash / WSL and run generate_mtls_certs.sh"
    }
}

$required = @("ca.crt", "client.crt", "server.crt")
$allExist = $true
foreach ($f in $required) {
    if (-not (Test-Path (Join-Path $Out $f))) { $allExist = $false }
}
if ($allExist) {
    Write-Host "mTLS certs already exist in $Out - delete them first to regenerate."
    exit 0
}

Push-Location $Out
try {
    openssl genrsa -out ca.key 4096
    openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt -subj "/C=IN/ST=Delhi/L=Delhi/O=IIITD ECE Portal/CN=ECE Portal mTLS CA"

    openssl genrsa -out server.key 2048
    openssl req -new -key server.key -out server.csr -subj "/C=IN/ST=Delhi/L=Delhi/O=IIITD ECE Portal/CN=ollama-proxy"

    $serverExt = @'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ollama-proxy
DNS.2 = localhost
IP.1 = 127.0.0.1
'@
    Set-Content -Path server.ext -Value $serverExt -Encoding ascii
    openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 825 -sha256 -extfile server.ext

    openssl genrsa -out client.key 2048
    openssl req -new -key client.key -out client.csr -subj "/C=IN/ST=Delhi/L=Delhi/O=IIITD ECE Portal/CN=ece-portal-backend"

    $clientExt = @'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
'@
    Set-Content -Path client.ext -Value $clientExt -Encoding ascii
    openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 825 -sha256 -extfile client.ext

    Remove-Item -Force -ErrorAction SilentlyContinue *.csr, *.ext, *.srl
}
finally {
    Pop-Location
}

Write-Host "Wrote mTLS materials to $Out"
Write-Host "Next: docker compose -f docker-compose.ollama.yml up -d"
