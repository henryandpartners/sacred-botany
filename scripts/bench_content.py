#!/usr/bin/env python3
"""Measure content-vs-reasoning token split for local models."""
import json, time, urllib.request

def bench(model, max_tokens):
    body = {"model": model,
            "messages": [{"role": "user", "content": "Write a short 3-sentence botanical profile of the kava plant (Piper methysticum)."}],
            "max_tokens": max_tokens, "temperature": 0.2}
    req = urllib.request.Request("http://127.0.0.1:1234/v1/chat/completions",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=280) as r:
            d = json.loads(r.read().decode())
    except Exception as e:
        print(f"{model}: ERROR {e}")
        return
    dt = time.time() - t0
    c = d["choices"][0]
    content = (c.get("message", {}).get("content") or "").strip()
    usage = d.get("usage", {})
    det = usage.get("completion_tokens_details", {})
    print(f"{model}: {dt:.1f}s total_tok={usage.get('completion_tokens')} "
          f"reasoning={det.get('reasoning_tokens')} finish={c.get('finish_reason')}")
    print(f"  content_len={len(content)}: {content[:150]!r}")

bench("qwen/qwen3.8-27b", 2000)
bench("prism-ml/bonsai-27b", 2000)
