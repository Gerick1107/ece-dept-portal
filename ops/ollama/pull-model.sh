#!/bin/sh
# Wait for the Ollama API, then pull LOCAL_LLM_MODEL (or OLLAMA_MODEL).
# Used by the ollama-pull service in docker-compose.ollama.yml.
set -eu

MODEL="${OLLAMA_MODEL:-${LOCAL_LLM_MODEL:-llama3.2:3b}}"
HOST="${OLLAMA_HOST:-http://ollama:11434}"
export OLLAMA_HOST="$HOST"

echo "ollama-pull: waiting for Ollama at $HOST …"
i=0
while [ "$i" -lt 90 ]; do
  if ollama list >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 2
done

if ! ollama list >/dev/null 2>&1; then
  echo "ollama-pull: ERROR — Ollama not reachable at $HOST after waiting" >&2
  exit 1
fi

echo "ollama-pull: ensuring model '$MODEL' is present …"
ollama pull "$MODEL"
echo "ollama-pull: done ($MODEL)."
