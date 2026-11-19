"""Optional language-model client for AI capability D (decision explanation).

Disabled unless configured through environment variables (no credentials in code, no paid API needed to run Mezan):
  MEZAN_LLM_PROVIDER   "openai" (default; any OpenAI-compatible /chat/completions endpoint) or "anthropic"
  MEZAN_LLM_API_KEY    API key
  MEZAN_LLM_MODEL      model name (required)
  MEZAN_LLM_BASE_URL   optional base URL (default https://api.openai.com/v1 or https://api.anthropic.com/v1)
  MEZAN_LLM_TIMEOUT    seconds (default 30)
The model only rewrites a verified, structured fact sheet; explain.verify_numbers() rejects any output containing a
number that is not in the fact sheet, and the deterministic explanation is shown instead.
"""
from __future__ import annotations

import os

SYSTEM = ("You write short, plain-English decision briefs for an industrial investment committee. Use ONLY the facts "
          "provided. Do not add, round differently, estimate or compute any number: copy numbers exactly as written in the "
          "facts. Do not claim certainty: probabilities are model outputs on simulated futures, not guarantees. If a fact is "
          "missing, say it is not available. Structure: Recommendation; Why it wins; Constraints; Main risks; What could "
          "change the decision; Is better information worth collecting. At most 220 words.")


def _load_dotenv(path=None):
    """Read KEY=VALUE lines from the project's .env (if present) without overriding variables already set."""
    from pathlib import Path
    f = Path(path) if path else Path(__file__).resolve().parents[1] / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k.strip().startswith("MEZAN_") and v.strip():
                os.environ.setdefault(k.strip(), v.strip())


def config():
    _load_dotenv()
    key, model = os.environ.get("MEZAN_LLM_API_KEY", ""), os.environ.get("MEZAN_LLM_MODEL", "")
    provider = os.environ.get("MEZAN_LLM_PROVIDER", "openai").lower()
    base = os.environ.get("MEZAN_LLM_BASE_URL") or ("https://api.anthropic.com/v1" if provider == "anthropic" else "https://api.openai.com/v1")
    return dict(enabled=bool(key and model), provider=provider, model=model, base_url=base.rstrip("/"),
                timeout=float(os.environ.get("MEZAN_LLM_TIMEOUT", "30")), _key=key)


def describe():
    c = config()
    return f"{c['provider']} · {c['model']}" if c["enabled"] else "not configured"


def complete(facts_text: str, cfg=None, post=None) -> str:
    """Return the model's text. `post` (callable(url, headers, json, timeout) -> dict) is injectable for tests."""
    c = cfg or config()
    if not c["enabled"]:
        raise RuntimeError("language model not configured")
    if post is None:
        import requests

        def post(url, headers, json, timeout):
            r = requests.post(url, headers=headers, json=json, timeout=timeout)
            r.raise_for_status()
            return r.json()
    user = "FACTS (verified outputs of the Mezan calculation engine):\n" + facts_text
    if c["provider"] == "anthropic":
        data = post(f"{c['base_url']}/messages", {"x-api-key": c["_key"], "anthropic-version": "2023-06-01",
                                                   "content-type": "application/json"},
                    {"model": c["model"], "max_tokens": 600, "system": SYSTEM, "messages": [{"role": "user", "content": user}]},
                    c["timeout"])
        return "".join(b.get("text", "") for b in data.get("content", []))
    data = post(f"{c['base_url']}/chat/completions", {"Authorization": f"Bearer {c['_key']}", "Content-Type": "application/json"},
                {"model": c["model"], "temperature": 0.2,
                 "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}, c["timeout"])
    return data["choices"][0]["message"]["content"]
