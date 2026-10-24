#!/usr/bin/env python3
"""Rough memory estimate for a model plus its context on a Mac with unified memory.

All model figures are approximate (typical Ollama downloads). Treat the result as a
planning aid, then confirm with `ollama ps` and Activity Monitor.
"""
from __future__ import annotations

import argparse

GIB = 1024**3

# name: (weights in GB, layers, KV heads, head dimension)
MODELS = {
    "qwen3:8b": (5.2, 36, 8, 128),
    "llama3.1:8b": (4.9, 32, 8, 128),
    "qwen2.5:7b": (4.7, 28, 4, 128),
    "qwen3:8b-q8_0": (8.9, 36, 8, 128),
    "qwen3:14b": (9.3, 40, 8, 128),
}

# bytes per stored KV element
KV_BYTES = {"f16": 2.0, "q8_0": 34 / 32, "q4_0": 18 / 32}


def kv_bytes_per_token(layers: int, kv_heads: int, head_dim: int, kv_type: str) -> float:
    """Keys and values (x2) for every layer."""
    return 2 * layers * kv_heads * head_dim * KV_BYTES[kv_type]


def estimate(model: str, num_ctx: int, kv_type: str, overhead_gb: float = 0.8) -> dict[str, float]:
    weights_gb, layers, kv_heads, head_dim = MODELS[model]
    kv_gb = kv_bytes_per_token(layers, kv_heads, head_dim, kv_type) * num_ctx / GIB
    return {"weights_gb": weights_gb, "kv_gb": kv_gb, "overhead_gb": overhead_gb, "total_gb": weights_gb + kv_gb + overhead_gb}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ram", type=float, default=16, help="unified memory in GB (default 16)")
    parser.add_argument("--usable", type=float, default=0.75, help="share of RAM the GPU may use (default 0.75, about 12 GB)")
    parser.add_argument("--ctx", type=int, default=16384, help="context length (num_ctx)")
    parser.add_argument("--kv", choices=sorted(KV_BYTES), default="q8_0", help="KV cache type")
    args = parser.parse_args(argv)
    budget = args.ram * args.usable
    print(f"RAM {args.ram:g} GB, GPU budget about {budget:.1f} GB, context {args.ctx}, KV cache {args.kv}")
    print(f"{'model':<16}{'weights':>9}{'KV':>8}{'other':>8}{'total':>8}   fits?")
    for name in MODELS:
        e = estimate(name, args.ctx, args.kv)
        verdict = "yes" if e["total_gb"] <= budget - 1.0 else ("tight" if e["total_gb"] <= budget else "no")
        print(f"{name:<16}{e['weights_gb']:>8.1f}G{e['kv_gb']:>7.1f}G{e['overhead_gb']:>7.1f}G{e['total_gb']:>7.1f}G   {verdict}")
    print("\nEstimates only. Check the real numbers with `ollama ps` while a model is loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
