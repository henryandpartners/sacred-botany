#!/usr/bin/env python3
"""Test /no_think prompt marker and enable_thinking:false on qwen3.8-27b."""
import json, time, urllib.request

def call(body, timeout=280):
    req = urllib.request.Request("http://127.0.0.1:1234/v1/chat/completions",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def test(label, body):
    t0 = time.time()
    try:
        d = call(body)
    except Exception as e:
        print(f"{label}: ERROR {e}"); return
    dt = time.time() - t0
    c = d["choices"][0]
    content = (c.get("message", {}).get("content") or "").strip()
    det = d.get("usage", {}).get("completion_tokens_details", {})
    print(f"{label}: {dt:.1f}s total={d.get('usage',{}).get('completion_tokens')} "
          f"reasoning={det.get('reasoning_tokens')} finish={c.get('finish_reason')} "
          f"content_len={len(content)}")

BASE = {"model": "qwen/qwen3.8-27b", "max_tokens": 1200, "temperature": 0.2,
        "messages": [{"role": "user", "content": "Write a 4-sentence field-identification note about peyote cactus."}]}

test("no_think-marker", {**BASE, "messages": [{"role": "user", "content": BASE["messages"][0]["content"] + "\n\n/no_think"}]})
t2 = {k: v for k, v in BASE.items()}
t2["chat_template_kwargs"] = {"enable_thinking": False}
test("enable_thinking_false", t2)
