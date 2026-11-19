"""Record model responses once, then replay them, so a Q&A regression run costs nothing.

Every model call of the service goes through httpx to the OpenAI API. In ``record`` mode each
request is sent and its response stored under a key made from the request body (model,
messages, schema); in ``replay`` mode the stored response is returned without a network call.
A request the tape already holds is answered from it in ``record`` mode too: questions on one
workbook send the same label-reading request, and a model answers it differently each time, so
asking again would change the prompts of questions recorded earlier.
A request the tape does not hold is answered with an error response and counted as a miss, so
a changed prompt shows up as "not recorded" instead of silently calling the paid API.
"""
import hashlib
import json
from pathlib import Path

import httpx

_HOSTS = ("api.openai.com",)


class Tape:
    def __init__(self, path, mode):
        if mode not in {"record", "replay"}:
            raise ValueError("mode must be record or replay")
        self.path, self.mode = Path(path), mode
        self.entries = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.misses, self.hits, self.recorded = [], 0, 0

    @staticmethod
    def key(request):
        body = request.content or b""
        try:
            body = json.dumps(json.loads(body), sort_keys=True, ensure_ascii=False).encode("utf-8")
        except (ValueError, UnicodeDecodeError):
            pass
        return hashlib.sha256(request.url.path.encode() + b"\n" + body).hexdigest()

    def holds(self, request):
        return self.key(request) in self.entries

    def lookup(self, request):
        entry = self.entries.get(self.key(request))
        if entry is None:
            self.misses.append(_summary(request))
            return httpx.Response(599, json={"error": {"message": "not recorded on the tape"}})
        self.hits += 1
        return httpx.Response(entry["status"], content=entry["body"].encode("utf-8"),
                              headers={"content-type": "application/json"})

    def store(self, request, response):
        if response.status_code == 200:
            self.entries[self.key(request)] = {"status": 200, "body": response.text, "request": _summary(request)}
            self.recorded += 1

    def save(self):
        if self.mode == "record":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.entries, ensure_ascii=False, indent=0), encoding="utf-8")
            temporary.replace(self.path)


def _summary(request):
    try:
        body = json.loads(request.content or b"{}")
    except ValueError:
        return {"path": request.url.path}
    messages = body.get("messages") or []
    last = str(messages[-1].get("content", ""))[:200] if messages else ""
    return {"path": request.url.path, "model": body.get("model"), "last_message": last}


def install(tape):
    """Route every request to the model API through the tape, at the transport every httpx client
    ends in. Newer OpenAI SDKs ship their own copy of httpx ("httpx2"); both are wrapped.
    Returns an undo function."""
    undos = [_wrap(module, tape) for module in _http_modules()]

    def undo():
        for item in undos:
            item()
    return undo


def _http_modules():
    modules = [httpx]
    try:
        import httpx2  # the OpenAI SDK's own copy, when installed
        modules.append(httpx2)
    except ImportError:
        pass
    return modules


def _wrap(module, tape):
    original_async = module.AsyncHTTPTransport.handle_async_request
    original_sync = module.HTTPTransport.handle_request

    def answer(request):
        stored = tape.lookup(request)
        return module.Response(stored.status_code, headers=dict(stored.headers), content=stored.content, request=request)

    def kept(request, response, body):
        # The body is already decoded: its compression and length headers no longer describe it.
        headers = {key: value for key, value in response.headers.items()
                   if key.lower() not in {"content-encoding", "content-length", "transfer-encoding"}}
        copy = module.Response(response.status_code, headers=headers, content=body, request=request)
        tape.store(request, copy)
        return copy

    async def handle_async(transport, request):
        if request.url.host not in _HOSTS:
            return await original_async(transport, request)
        if tape.mode == "replay" or tape.holds(request):
            return answer(request)
        response = await original_async(transport, request)
        return kept(request, response, await response.aread())

    def handle_sync(transport, request):
        if request.url.host not in _HOSTS:
            return original_sync(transport, request)
        if tape.mode == "replay" or tape.holds(request):
            return answer(request)
        response = original_sync(transport, request)
        return kept(request, response, response.read())

    module.AsyncHTTPTransport.handle_async_request = handle_async
    module.HTTPTransport.handle_request = handle_sync

    def undo():
        module.AsyncHTTPTransport.handle_async_request = original_async
        module.HTTPTransport.handle_request = original_sync
    return undo
