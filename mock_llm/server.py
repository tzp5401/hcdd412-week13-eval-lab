"""Mock LLM service for HCDD 412 (Week 13 starter; reused in the Week 14 pen-test lab).

A tiny, deterministic stand-in for a hosted model. It speaks the same wire format
as an OpenAI-style /v1/chat/completions endpoint, so the app talks to it exactly as
it would talk to a real model -- but it costs nothing, needs no API key, and gives
the same answer every time, which is what makes evals repeatable.

HOW THE MOCK "THINKS" (deliberately simple and documented, so you can reason about it):

1. It reads the last user message, which the app builds as:
       Context:
       - <policy line>
       - <policy line>
       Question: <the student's question>
2. It decides whether any context line supports the question (two or more shared
   content words after stop-word removal).
3. If a line supports the question, it answers from that line.
4. If NOTHING supports the question, its behavior depends on the system prompt:
   - If the system prompt tells it to use ONLY the provided context (it looks for the
     phrase "only the provided context"), it says it does not have that information.
   - Otherwise it makes up a confident, plausible-sounding answer. That is the flaw
     your evals need to catch. (Real models do this too; this one does it on purpose.)

OPTIONAL (Week 14 pen-test lab): set MOCK_COMPLIANCE=naive and the mock will obey
instructions that appear inside the retrieved context, which simulates a model that is
vulnerable to prompt injection. Default is "strict" (ignores such instructions).
"""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("PORT", "9000"))
COMPLIANCE = os.environ.get("MOCK_COMPLIANCE", "strict").lower()

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "in", "on", "at",
    "for", "and", "or", "if", "i", "me", "my", "do", "does", "can", "how", "what",
    "when", "where", "who", "which", "it", "this", "that", "there", "from", "by",
    "with", "get", "much", "any", "s",
}

REFUSAL = "I don't have that information. Please contact the Student Services office."
HALLUCINATION = (
    "Absolutely! That is available to all students. Just visit Student Services "
    "and ask for the approved exception; it will be granted automatically."
)


def stem(word):
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def content_words(text):
    words = re.findall(r"[a-z0-9$']+", text.lower())
    cleaned = []
    for w in words:
        w = w.replace("'", " ").split()[0] if "'" in w else w
        if w and w not in STOP_WORDS:
            cleaned.append(stem(w))
    return set(cleaned)


def parse_user_message(text):
    context_lines = []
    question = ""
    in_context = False
    for line in text.splitlines():
        if line.startswith("Context:"):
            in_context = True
            continue
        if line.startswith("Question:"):
            question = line[len("Question:"):].strip()
            in_context = False
            continue
        if in_context and line.startswith("- "):
            context_lines.append(line[2:].strip())
    return context_lines, question


def best_support(context_lines, question):
    q_words = content_words(question)
    best, best_score = None, 0
    for line in context_lines:
        score = len(q_words & content_words(line))
        if score > best_score:
            best, best_score = line, score
    return best if best_score >= 2 else None


def respond(messages):
    system = " ".join(m["content"] for m in messages if m["role"] == "system").lower()
    user = [m["content"] for m in messages if m["role"] == "user"][-1]
    context_lines, question = parse_user_message(user)

    if COMPLIANCE == "naive":
        for line in context_lines:
            match = re.search(r"ignore (all )?previous instructions[:.]?\s*(.*)", line, re.I)
            if match:
                return match.group(2) or "OK, ignoring my earlier instructions."

    support = best_support(context_lines, question)
    if support:
        return f"Based on campus policy: {support}"
    if "only the provided context" in system:
        return REFUSAL
    return HALLUCINATION


def count_tokens(text):
    return max(1, len(text.split()))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok", "compliance": COMPLIANCE})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
            messages = data["messages"]
        except (ValueError, KeyError):
            self._send(400, {"error": "expected JSON with a 'messages' list"})
            return
        answer = respond(messages)
        prompt_tokens = sum(count_tokens(m["content"]) for m in messages)
        completion_tokens = count_tokens(answer)
        self._send(200, {
            "id": "mock-0001",
            "object": "chat.completion",
            "model": "mock-llm-1",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": answer}}],
            "usage": {"prompt_tokens": prompt_tokens,
                      "completion_tokens": completion_tokens,
                      "total_tokens": prompt_tokens + completion_tokens},
        })

    def log_message(self, fmt, *args):  # keep container logs quiet
        pass


if __name__ == "__main__":
    print(f"mock-llm listening on 0.0.0.0:{PORT} (compliance={COMPLIANCE})", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
