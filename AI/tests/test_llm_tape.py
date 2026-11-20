"""Model responses recorded once are replayed without a network call; an unrecorded call is a miss."""
import asyncio

import httpx

from evals.regression.llm_tape import Tape, install

URL = "https://api.openai.com/v1/chat/completions"


CALLS = []


async def _network(transport, request):  # stands in for the real transport the tape wraps
    CALLS.append(request)
    return httpx.Response(200, json={"echo": __import__("json").loads(request.content)})


def _post(body):
    CALLS.clear()

    async def send():
        async with httpx.AsyncClient() as client:
            return await client.post(URL, json=body)
    return asyncio.run(send()), list(CALLS)


def test_a_recorded_response_is_replayed_and_an_unrecorded_one_is_a_miss(tmp_path, monkeypatch):
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _network)
    path = tmp_path / "tape.json"
    recording = Tape(path, "record")
    undo = install(recording)
    try:
        response, calls = _post({"model": "m", "messages": [{"role": "user", "content": "지진"}]})
    finally:
        undo()
    recording.save()
    assert response.json() == {"echo": {"model": "m", "messages": [{"role": "user", "content": "지진"}]}} and len(calls) == 1

    replaying = Tape(path, "replay")
    undo = install(replaying)
    try:
        again, calls = _post({"messages": [{"role": "user", "content": "지진"}], "model": "m"})  # key order differs
        other, _ = _post({"model": "m", "messages": [{"role": "user", "content": "홍수"}]})
    finally:
        undo()
    assert again.json() == response.json() and calls == [] and replaying.hits == 1
    assert other.status_code == 599 and len(replaying.misses) == 1
