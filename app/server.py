"""Thin HTTP wrapper around the assistant. Binds to all interfaces INSIDE the container;
docker-compose publishes it on 127.0.0.1 only (your machine, nobody else's)."""

import os

from flask import Flask, jsonify, request

import assistant

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(status="ok", prompt_version=assistant.PROMPT_VERSION)


@app.post("/ask")
def ask():
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify(error="Provide a non-empty 'question'."), 400
    if len(question) > 500:
        return jsonify(error="Question too long (500 character limit)."), 400
    return jsonify(assistant.ask(question))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
