"""Model gateway: any model behind an OpenAI-compatible chat endpoint.

Ollama (local), vLLM, llama.cpp server and hosted APIs all speak this shape, so
adding a model means three facts: base URL, model name, optional API key.
The key never reaches the model and never leaves this module.
"""
import json
import os
import pathlib
import subprocess
import tempfile
import urllib.error
import urllib.request

PROVIDERS = {"ollama": ("http://127.0.0.1:11434/v1", None),
             "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
             "anthropic": ("https://api.anthropic.com/v1", "ANTHROPIC_API_KEY"),
             "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY")}


class Model:
    def __init__(self, spec, base_url=None, api_key=None, timeout=180):
        provider, _, name = spec.partition(":")
        default_url, key_env = PROVIDERS.get(provider, (None, None))
        if default_url is None and not base_url:
            raise ValueError(f"bilinmeyen saglayici '{provider}': --base-url verin")
        self.name, self.spec, self.timeout = name, spec, timeout
        self.base_url = (base_url or os.environ.get("VARDIYA_BASE_URL") or default_url).rstrip("/")
        self.api_key = api_key or os.environ.get("VARDIYA_API_KEY") or (os.environ.get(key_env) if key_env else None)
        self.calls = 0
        self.think = os.environ.get("VARDIYA_THINK", "0") == "1"

    def chat(self, messages):
        if self.spec.startswith("ollama:") and self.base_url.endswith("/v1"):
            return self._chat_ollama(messages)
        body = {"model": self.name, "messages": messages, "temperature": 0, "seed": 0,
                "response_format": {"type": "json_object"}}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        req = urllib.request.Request(self.base_url + "/chat/completions", json.dumps(body).encode(), headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            self.calls += 1
            return json.loads(r.read())["choices"][0]["message"]["content"]

    def _chat_ollama(self, messages):
        """Ollama's own API: lets each request fix the context size, so a huge server-wide
        default does not make every model load with a 100k+ token window."""
        body = {"model": self.name, "messages": messages, "stream": False, "format": "json",
                "options": {"temperature": 0, "seed": 0, "num_ctx": int(os.environ.get("VARDIYA_NUM_CTX", 16384))}}
        # Reasoning models write long hidden "thinking" before each answer (tens of seconds per call on
        # a laptop GPU). It is off by default, for every arm alike; VARDIYA_THINK=1 turns it on.
        if self.think is not None:
            body["think"] = self.think
        for attempt in (0, 1):
            req = urllib.request.Request(self.base_url[:-3] + "/api/chat", json.dumps(body).encode(),
                                         {"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    self.calls += 1
                    return json.loads(r.read())["message"]["content"]
            except urllib.error.HTTPError as e:
                if attempt or e.code != 400 or "think" not in body:
                    raise
                del body["think"]  # this model has no thinking switch
                self.think = None

    def ask_json(self, messages, retries=2):
        """Schema repair loop: small models often wrap or break JSON."""
        for _ in range(retries + 1):
            try:
                text = self.chat(messages)
                start, end = text.find("{"), text.rfind("}")
                return json.loads(text[start:end + 1])
            except (ValueError, KeyError, IndexError):
                messages = messages + [{"role": "user", "content": "Reply with one valid JSON object only."}]
        return None

    def choose(self, question, options, context):
        """Guided mode: the model picks one enumerated option. Nothing else is accepted."""
        prompt = (f"{context}\n\nQuestion: {question}\nOptions:\n"
                  + "\n".join(f"- {k}: {v}" for k, v in options.items())
                  + '\n\nReply with JSON: {"choice": "<one option key>", "why": "<one sentence>"}')
        out = self.ask_json([{"role": "system", "content": "You are a careful batch operations analyst."},
                             {"role": "user", "content": prompt}])
        if isinstance(out, dict) and out.get("choice") in options:
            return out["choice"], str(out.get("why", ""))
        return None, "gecersiz cikti"


class AgyModel:
    """A model reached through the Antigravity command-line tool (`agy`), for models that have no API
    key on this machine. Spec: `agy:<model id>`, ids from `agy models`.

    The tool is an agent, so it is run in an empty directory: it has nothing to read and is only
    asked for text. A conversation is continued by id, so each turn sends only the new message."""
    CHUNK = 9000

    def __init__(self, spec, timeout=420, **_):
        self.spec, self.name, self.timeout, self.calls = spec, spec.partition(":")[2], timeout, 0
        self.think = None
        self._sent, self._conversation, self.tokens = [], None, 0
        self._cwd =pathlib.Path(tempfile.gettempdir()).resolve() / "vardiya-agy-bos"
        self._cwd.mkdir(exist_ok=True)

    def chat(self, messages):
        n = len(self._sent)
        if self._conversation and messages[:n] == self._sent and len(messages) == n + 2 \
                and messages[n]["role"] == "assistant" and messages[n + 1]["role"] == "user":
            prompt, extra = messages[-1]["content"], ["--conversation", self._conversation]
        else:
            prompt = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in messages)
            extra = []
        prompt += "\n\nDo not use any tools. Reply with ONE JSON object only, no other text."
        # The prompt travels on the command line (about 32,000 characters at most on Windows). A long one goes
        # in parts within the same conversation; only the answer to the last part counts.
        parts = [prompt[i:i + self.CHUNK] for i in range(0, len(prompt), self.CHUNK)] or [""]
        out = {}
        for k, part in enumerate(parts, 1):
            if len(parts) > 1 and k < len(parts):
                part = (f"[PART {k} of {len(parts)} of one long message. Do not act on it yet. "
                        f'Reply only with {{"part": {k}}}.]\n\n' + part)
            elif len(parts) > 1:
                part = f"[PART {k} of {len(parts)}, the last one. Now answer the whole message.]\n\n" + part
            cmd = ["agy", "--model", self.name, "--output-format", "json", "--print-timeout", f"{self.timeout}s"] + extra + ["-p=" + part]
            try:
                run = subprocess.run(cmd, cwd=self._cwd, capture_output=True, text=True, encoding="utf-8",
                                     errors="replace", timeout=self.timeout + 30)
                out = json.loads(run.stdout.strip().splitlines()[-1])
            except (subprocess.TimeoutExpired, ValueError, IndexError, OSError) as e:
                raise urllib.error.URLError(f"agy cagrisi basarisiz: {e}") from None
            if out.get("status") != "SUCCESS":
                raise urllib.error.URLError(f"agy durumu: {out.get('status')}")
            self.calls += 1
            self.tokens += (out.get("usage") or {}).get("total_tokens", 0)
            if out.get("conversation_id"):
                extra = ["--conversation", out["conversation_id"]]
        self._sent, self._conversation = list(messages), out.get("conversation_id")
        return out.get("response", "")

    ask_json = None  # filled in below: same repair loop and narrow question as Model
    choose = None


class FakeModel:
    """Scripted stand-in for tests and for the code-share ablation arm."""
    spec = "fake"

    def __init__(self, choices=(), actions=()):
        self.choices, self.actions, self.calls = list(choices), list(actions), 0

    def choose(self, question, options, context):
        self.calls += 1
        return (self.choices.pop(0) if self.choices else None), "scripted"

    def ask_json(self, messages, retries=2):
        self.calls += 1
        return self.actions.pop(0) if self.actions else {"verb": "done"}


AgyModel.ask_json, AgyModel.choose = Model.ask_json, Model.choose


def connect(spec, base_url=None, timeout=150):
    """The model behind a spec: `agy:<id>` goes through the Antigravity CLI, anything else through HTTP."""
    if spec.startswith("agy:"):
        return AgyModel(spec, timeout=max(timeout, 420))
    return Model(spec, base_url=base_url, timeout=timeout)


def list_ollama(base="http://localhost:11434"):
    with urllib.request.urlopen(base + "/api/tags", timeout=5) as r:
        return [m["name"] for m in json.loads(r.read()).get("models", [])]
