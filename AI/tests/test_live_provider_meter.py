import json
from decimal import Decimal
import pytest
import httpx
from evals.live_provider_meter import ProviderMeter, LiveEvaluationStopped

PRICES = {'gpt-4.1-2025-04-14': {'input': 2, 'cached_input': .5, 'output': 8}}
PAYLOAD = {'model': 'gpt-4.1-2025-04-14', 'messages': [], 'max_completion_tokens': 100}
USAGE = {'prompt_tokens': 1000, 'completion_tokens': 100, 'prompt_tokens_details': {'cached_tokens': 200}}
URL = 'https://api.openai.com/v1/chat/completions'


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
@pytest.mark.parametrize('module_name', ['httpx', 'httpx2'])
async def test_real_transport_classes_meter_async_and_sync_without_network(tmp_path, module_name):
    module = pytest.importorskip(module_name)
    def response(request):
        return module.Response(200, headers={'x-request-id': 'test-id'}, json={'usage': USAGE, 'choices': []})
    meter = ProviderMeter(tmp_path / 'ledger.json', PRICES)
    meter.case_id.set('sample')
    with meter.installed():
        async with module.AsyncClient(transport=module.MockTransport(response)) as client:
            await client.post(URL, json=PAYLOAD, headers={'Authorization': 'Bearer never-store-this'})
        with module.Client(transport=module.MockTransport(response)) as client:
            client.post(URL, json=PAYLOAD)
    result = meter.summary()
    assert result['http_requests'] == result['successful_requests'] == 2
    assert result['input_tokens'] == 2000 and result['cached_input_tokens'] == 400
    assert Decimal(result['estimated_usd']) == Decimal('.005')
    assert result['metering_complete']
    assert 'never-store-this' not in meter.path.read_text()
    assert all(c['case_id'] == 'sample' for c in meter.calls)


@pytest.mark.anyio
async def test_actual_openai_sdk_uses_instrumented_transport(tmp_path):
    httpx2 = pytest.importorskip('httpx2')
    from openai import AsyncOpenAI
    def response(request):
        return httpx2.Response(200, json={'id': 'chatcmpl-test', 'object': 'chat.completion', 'created': 1,
            'model': PAYLOAD['model'], 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'test'}, 'finish_reason': 'stop'}], 'usage': USAGE})
    meter = ProviderMeter(tmp_path / 'sdk.json', PRICES)
    with meter.installed():
        async with AsyncOpenAI(api_key='test-only', http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(response))) as sdk:
            result = await sdk.chat.completions.create(**PAYLOAD)
            assert result.usage.prompt_tokens == 1000
    assert meter.summary()['http_requests'] == 1
    assert meter.summary()['metering_complete']


@pytest.mark.anyio
async def test_missing_usage_stops_and_never_becomes_zero_cost_success(tmp_path):
    meter = ProviderMeter(tmp_path / 'missing.json', PRICES)
    with meter.installed(), pytest.raises(LiveEvaluationStopped, match='lacks usage'):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))) as client:
            await client.post(URL, json=PAYLOAD)
    assert not meter.summary()['metering_complete']
    assert meter.summary()['incomplete_requests'] == [1]


@pytest.mark.anyio
async def test_request_limit_blocks_before_second_network_attempt(tmp_path):
    visited = []
    def response(request):
        visited.append(request)
        return httpx.Response(200, json={'usage': USAGE})
    meter = ProviderMeter(tmp_path / 'bounded.json', PRICES, max_requests=1)
    with meter.installed():
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
            await client.post(URL, json=PAYLOAD)
            with pytest.raises(LiveEvaluationStopped, match='ceiling'):
                await client.post(URL, json=PAYLOAD)
    assert len(visited) == 1 and len(meter.calls) == 1


def test_existing_ledger_never_overwritten(tmp_path):
    path = tmp_path / 'exists.json'
    path.write_text('{}')
    with pytest.raises(FileExistsError):
        ProviderMeter(path, PRICES)
