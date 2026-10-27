"""Opt-in evaluator-only HTTP usage ledger. Never imported by production routes.

Wrap both SDK HTTP transports (httpx/httpx2), including retries, before live
evaluation. Prices are supplied explicitly, not inferred from a model alias.
No request headers, credentials or full prompts are persisted.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from decimal import Decimal
import importlib
import json
from pathlib import Path
import time
from unittest.mock import patch


class LiveEvaluationStopped(BaseException):
    """Cannot be swallowed by application model-fallback exception handlers."""


class ProviderMeter:
    def __init__(self, path, prices, *, max_requests=60, max_usd=3, local_hosts=()):
        self.path = Path(path)
        if self.path.exists():
            raise FileExistsError('Refusing to overwrite a paid evaluation ledger')
        self.prices = prices
        self.max_requests, self.max_usd = max_requests, Decimal(str(max_usd))
        self.local_hosts = set(local_hosts)
        self.case_id = ContextVar('provider_meter_case', default='setup')
        self.calls, self.stop = [], None

    def _cost(self, model, usage):
        rate = self.prices[model]
        prompt, output = usage['prompt_tokens'], usage['completion_tokens']
        cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens', 0)
        if not all(isinstance(n, int) and n >= 0 for n in (prompt, output, cached)) or cached > prompt:
            raise ValueError('Invalid provider usage counters')
        return ((prompt - cached) * Decimal(str(rate['input'])) + cached * Decimal(str(rate['cached_input']))
                + output * Decimal(str(rate['output']))) / 1_000_000

    def summary(self):
        used = [c for c in self.calls if 'usage' in c]
        incomplete = [c['index'] for c in self.calls if c.get('http_status') == 200 and 'estimated_usd' not in c
                      or c.get('state') != 'complete']
        return {'http_requests': len(self.calls), 'successful_requests': sum(c.get('http_status') == 200 for c in self.calls),
                'input_tokens': sum(c['usage']['prompt_tokens'] for c in used),
                'cached_input_tokens': sum((c['usage'].get('prompt_tokens_details') or {}).get('cached_tokens', 0) for c in used),
                'output_tokens': sum(c['usage']['completion_tokens'] for c in used),
                'estimated_usd': str(sum((Decimal(c.get('estimated_usd', '0')) for c in self.calls), Decimal(0))),
                'metering_complete': not incomplete, 'incomplete_requests': incomplete,
                'cost_note': 'Provider-reported tokens × explicitly recorded standard rates; estimate, not billing ledger or tax/credit-adjusted charge.'}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({'calls': self.calls, 'totals': self.summary(), 'prices_per_million': self.prices,
                                       'stop': self.stop}, ensure_ascii=False, indent=2, default=str))

    def _halt(self, reason):
        self.stop = reason
        self.save()
        raise LiveEvaluationStopped(reason)

    def _start(self, request):
        if request.url.host in self.local_hosts:
            return None
        if self.stop:
            raise LiveEvaluationStopped(self.stop)
        if (request.url.host != 'api.openai.com' or request.url.path != '/v1/chat/completions'
                or request.url.scheme != 'https'):
            self._halt('Unexpected external endpoint blocked')
        payload = json.loads(request.content)
        model = payload.get('model')
        if model not in self.prices or payload.get('stream'):
            self._halt('Unpriced model or unsupported streaming request blocked')
        rate = self.prices[model]
        reservation = (len(request.content) * Decimal(str(rate['input']))
                       + payload.get('max_completion_tokens', payload.get('max_tokens', 32768))
                       * Decimal(str(rate['output']))) / 1_000_000
        reserved = sum((Decimal(c['reserved_usd']) for c in self.calls if c['state'] == 'started'), Decimal(0))
        if (len(self.calls) >= self.max_requests
                or Decimal(self.summary()['estimated_usd']) + reserved + reservation > self.max_usd):
            self._halt('Evaluation request/cost ceiling reached')
        call = {'index': len(self.calls) + 1, 'case_id': self.case_id.get(), 'model': model,
                'schema': payload.get('response_format', {}).get('json_schema', {}).get('name'),
                'state': 'started', 'started_at': datetime.now(timezone.utc).isoformat(),
                'request_bytes': len(request.content), 'reserved_usd': str(reservation)}
        self.calls.append(call)
        self.save()  # Crash/interruption cannot erase an in-flight request.
        return call

    def _finish(self, call, response, elapsed):
        call.update(http_status=response.status_code, request_id=response.headers.get('x-request-id'), seconds=round(elapsed, 3))
        body = response.json()
        if response.status_code != 200:
            error = body.get('error') or {}
            call.update(state='complete', error={k: error.get(k) for k in ('type', 'code')})
            self._halt(f"Provider HTTP {response.status_code}: {error.get('code') or error.get('type') or 'unknown'}")
        usage = body.get('usage')
        if not isinstance(usage, dict) or not {'prompt_tokens', 'completion_tokens'} <= usage.keys():
            self._halt('Successful provider response lacks usage; refusing unmetered continuation')
        call.update(usage=usage, estimated_usd=str(self._cost(call['model'], usage)),
                    response_model=body.get('model'), choices=body.get('choices', []), state='complete')
        self.save()

    @contextmanager
    def installed(self):
        patches, seen = [], set()
        try:
            for name in ('httpx', 'httpx2'):
                try:
                    module = importlib.import_module(name)
                except ImportError:
                    continue
                for cls, asynchronous in ((module.AsyncClient, True), (module.Client, False)):
                    if cls in seen:
                        continue
                    seen.add(cls)
                    original = cls.send
                    if asynchronous:
                        async def send(client, request, *args, _send=original, **kwargs):
                            call, started = self._start(request), time.monotonic()
                            try:
                                response = await _send(client, request, *args, **kwargs)
                                if call is not None:
                                    await response.aread()
                                    self._finish(call, response, time.monotonic() - started)
                                return response
                            except Exception as error:
                                if call is None:
                                    raise
                                call.update(exception_type=type(error).__name__, seconds=round(time.monotonic() - started, 3))
                                self._halt(f'Provider transport/usage exception: {type(error).__name__}')
                    else:
                        def send(client, request, *args, _send=original, **kwargs):
                            call, started = self._start(request), time.monotonic()
                            try:
                                response = _send(client, request, *args, **kwargs)
                                if call is not None:
                                    response.read()
                                    self._finish(call, response, time.monotonic() - started)
                                return response
                            except Exception as error:
                                if call is None:
                                    raise
                                call.update(exception_type=type(error).__name__, seconds=round(time.monotonic() - started, 3))
                                self._halt(f'Provider transport/usage exception: {type(error).__name__}')
                    p = patch.object(cls, 'send', send)
                    p.start()
                    patches.append(p)
            self.save()
            yield self
        finally:
            for p in reversed(patches):
                p.stop()
            self.save()
