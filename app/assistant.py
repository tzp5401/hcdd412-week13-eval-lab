"""CampusConnect FAQ assistant: the 'AI feature' you will evaluate in Week 13.

Flow: question -> retrieve relevant policy lines -> build prompt -> call the model
-> return the answer plus run metadata (prompt version, latency, token usage).

The metadata is what makes this feature operable (the LLMOps part): every answer can
be traced to the prompt version that produced it.
"""

import json
import os
import re
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:9000/v1")
PROMPT_VERSION = os.environ.get("PROMPT_VERSION", "v1")
TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "10"))

STOP_WORDS = {
    "a", "an", "the", "is", "are", "to", "of", "in", "on", "at", "for", "and", "or",
    "i", "my", "do", "does", "can", "how", "what", "when", "where", "it", "this",
    "if", "get", "much", "any",
}


def load_policies():
    with open(BASE_DIR / "data" / "policies.json", encoding="utf-8") as handle:
        return json.load(handle)["policies"]


def load_prompt(version=None):
    version = version or PROMPT_VERSION
    path = BASE_DIR / "prompts" / f"{version}.txt"
    if not path.exists():
        raise FileNotFoundError(f"No prompt file for version '{version}': {path}")
    return path.read_text(encoding="utf-8").strip()


def _words(text):
    found = re.findall(r"[a-z0-9$]+", text.lower())
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w
            for w in found if w not in STOP_WORDS}


def retrieve(question, policies, k=3):
    """Keyword-overlap retrieval. Deliberately simple; good enough for this lab."""
    q_words = _words(question)
    scored = []
    for policy in policies:
        score = len(q_words & _words(policy))
        if score > 0:
            scored.append((score, policy))
    scored.sort(key=lambda pair: -pair[0])
    return [policy for _, policy in scored[:k]]


def build_messages(question, context, system_prompt):
    context_block = "\n".join(f"- {line}" for line in context) or "- (no matching policy found)"
    user = f"Context:\n{context_block}\nQuestion: {question}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ]


def ask(question, prompt_version=None):
    version = prompt_version or PROMPT_VERSION
    system_prompt = load_prompt(version)
    context = retrieve(question, load_policies())
    messages = build_messages(question, context, system_prompt)

    started = time.perf_counter()
    response = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        json={"model": "mock-llm-1", "messages": messages},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    latency_ms = round((time.perf_counter() - started) * 1000, 1)

    payload = response.json()
    return {
        "answer": payload["choices"][0]["message"]["content"],
        "prompt_version": version,
        "latency_ms": latency_ms,
        "total_tokens": payload.get("usage", {}).get("total_tokens", 0),
    }
