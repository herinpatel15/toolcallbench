# Model guide for a MacBook M4 with 16 GB

All sizes below are **approximate**. Confirm with `ollama ps` while a model is loaded, and
with `python scripts/estimate_memory.py` before you pull something large.

## Memory budget

Apple silicon shares one pool of memory between the CPU and GPU. By default macOS lets the
GPU use roughly three quarters of it on a 16 GB machine, so plan for **about 12 GB**, and
remember that macOS, your browser and your editor need memory too.

Memory used by a loaded model is:

```
weights  +  KV cache  +  small overhead
```

- **Weights**: fixed by the model and quantization. Q4_K_M is about 4.5 to 5 bits per weight; Q8_0 about 8.5.
- **KV cache**: grows with context length. Bytes per token = 2 x layers x KV heads x head size x bytes per element. For an 8B Qwen3-class model (36 layers, 8 KV heads, head size 128) that is 144 KiB per token with a 16-bit cache, so **16384 tokens = 2.25 GiB**. With `q8_0` the cache is about half that.

| Model (Q4_K_M unless noted) | Weights | KV at 16k, f16 | KV at 16k, q8_0 | Total at 16k, q8_0 | Verdict |
| --- | --- | --- | --- | --- | --- |
| qwen3:8b | ~5.2 GB | 2.3 GB | 1.2 GB | ~7 GB | comfortable |
| llama3.1:8b | ~4.9 GB | 2.0 GB | 1.1 GB | ~7 GB | comfortable |
| qwen2.5:7b | ~4.7 GB | 0.9 GB | 0.5 GB | ~6 GB | comfortable |
| qwen3:8b-q8_0 | ~8.9 GB | 2.3 GB | 1.2 GB | ~11 GB | works, little headroom |
| qwen3:14b | ~9.3 GB | 2.5 GB | 1.3 GB | ~11.4 GB | tight; close other apps |

Anything much bigger than 14B at Q4 will not fit in a useful way.

## Settings that matter

| Setting | Recommended | Why |
| --- | --- | --- |
| `num_ctx` | 16384 (8192 for Q8 or 14B) | Ollama's default (4096 on machines under 24 GB) can cut off multi-step conversations |
| `OLLAMA_FLASH_ATTENTION` | 1 | needed for a quantized KV cache |
| `OLLAMA_KV_CACHE_TYPE` | `q8_0` | roughly halves cache memory; `q4_0` saves more but may hurt quality |
| `OLLAMA_MAX_LOADED_MODELS` | 1 | no room for two |
| `OLLAMA_NUM_PARALLEL` | 1 | the benchmark is sequential |
| `--think off` | for Qwen3 and other thinking models | removes long reasoning before each call; compare both settings once |

`scripts/serve_ollama.sh` sets these. Record them in the report with `--kv-cache-type` and
`--flash-attention` or by using a config file.

## Which models to try first

1. **qwen3:8b** - supports tools and thinking; strong at following formats for its size.
2. **llama3.1:8b** - widely used baseline for tool calling.
3. **qwen2.5:7b** - smaller KV cache, so it leaves more room.

Pick any model whose Ollama page lists the **tools** capability. `toolcallbench doctor`
reports what your Ollama version says about each model.

## Questions the benchmark can answer for you

- Does Q4_K_M give up tool-calling accuracy compared with Q8_0? (`configs/quant-sweep-qwen3-8b.yaml`)
- Does turning thinking off help or hurt?
- Does a `q8_0` KV cache change results? Run twice with different server settings and **declare each one**.
- Is the faster model also reliable?

## Keeping the Mac healthy

A long benchmark keeps the GPU busy for a long time. Plug in the charger, keep the lid open
and the vents free, and use `caffeinate -i toolcallbench run ...` so the Mac does not sleep
mid-run (resume works if it does).

## Not verified

The figures here come from model configurations and formulas, not from measurements on your
machine. The first thing to do after your first run is to compare `ollama ps` with the table.
