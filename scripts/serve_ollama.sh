#!/usr/bin/env bash
# Start Ollama with settings suited to a MacBook with 16 GB of unified memory.
# Quit the Ollama menu-bar app first: it already owns port 11434 with its own settings.
set -euo pipefail

export OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH:-16384}"  # default context for every request
export OLLAMA_FLASH_ATTENTION=1                                 # required for a quantized KV cache
export OLLAMA_KV_CACHE_TYPE="${OLLAMA_KV_CACHE_TYPE:-q8_0}"     # f16 | q8_0 | q4_0
export OLLAMA_MAX_LOADED_MODELS=1                               # one model at a time; 16 GB has no room for two
export OLLAMA_NUM_PARALLEL=1                                    # the benchmark sends one request at a time

echo "Starting Ollama: context=${OLLAMA_CONTEXT_LENGTH} kv-cache=${OLLAMA_KV_CACHE_TYPE} flash-attention=on"
echo "Tell ToolCallBench about it:  --kv-cache-type ${OLLAMA_KV_CACHE_TYPE} --flash-attention  (or use configs/m4-16gb.yaml)"
exec ollama serve
