#!/bin/bash
AUTOMATION=$1
PREWARM_MIN=${2:-15}

declare -A MODELS=(
  ["job-automation"]="qwen2.5-coder:3b-instruct-q4_K_M"
  ["pinterest"]="llama3.2:3b-instruct-q4_K_M"
  ["linkedin-outreach"]="llama3.2:3b-instruct-q4_K_M"
)

EMBEDDING="nomic-embed-text:latest"
OLLAMA="http://localhost:11434"
MODEL=${MODELS[$AUTOMATION]}

if [[ -z "$MODEL" ]]; then
  echo "Usage: $0 {job-automation|pinterest|linkedin-outreach} [prewarm_minutes]"
  exit 1
fi

# Unload non-essential models (keep embeddings)
echo "🔄 Unloading non-essential models..."
for m in $(curl -s "$OLLAMA/api/ps" | jq -r '.models[].name' 2>/dev/null); do
  if [[ "$m" != "$EMBEDDING" ]]; then
    echo "  Unloading $m..."
    curl -s -X DELETE "$OLLAMA/api/generate" -H "Content-Type: application/json" -d "{\"model\":\"$m\"}" > /dev/null
  fi
done

# Load target model + embeddings
echo "🔄 Loading $MODEL..."
curl -s -X POST "$OLLAMA/api/generate" -H "Content-Type: application/json" -d "{\"model\":\"$MODEL\",\"prompt\":\"\",\"stream\":false}" > /dev/null

echo "🔄 Loading $EMBEDDING..."
curl -s -X POST "$OLLAMA/api/generate" -H "Content-Type: application/json" -d "{\"model\":\"$EMBEDDING\",\"prompt\":\"\",\"stream\":false}" > /dev/null

echo "✅ Models ready for $AUTOMATION. Keeping warm for ${PREWARM_MIN}min..."
sleep $((PREWARM_MIN * 60))