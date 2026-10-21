import assert from 'node:assert/strict'
import test from 'node:test'

import { MutationObserver, QueryClient } from '@tanstack/react-query'

import {
  applyScopedResult,
  createAsyncViewScope,
  unwrapScopedResult,
} from '../src/hooks/asyncViewScope.ts'
import { deferredJob } from './analysisJob.fixtures.ts'

for (const change of ['account switch', 'file switch', 'unmount']) {
  test(`late download cannot click a link or update cache after ${change}`, async () => {
    const client = new QueryClient()
    const scope = createAsyncViewScope()
    const leave = scope.mount()
    const pending = deferredJob<string>()
    let effects = 0
    const observer = new MutationObserver(client, {
      mutationFn: () => scope.run(() => pending.promise),
      onSuccess: (result) =>
        applyScopedResult(result, () => {
          effects += 1
        }),
    })
    const unsubscribe = observer.subscribe(() => {})
    const request = observer.mutate()
    const rejected = assert.rejects(request, { name: 'AbortError' })
    await Promise.resolve()
    leave()
    unsubscribe()
    client.clear()
    pending.resolve('private workbook')
    await rejected
    assert.equal(effects, 0)
  })
}

test('StrictMode remount permits new requests but does not revive the old lease', async () => {
  const scope = createAsyncViewScope()
  const leaveFirst = scope.mount()
  const pending = deferredJob<string>()
  const first = scope.run(() => pending.promise)
  const rejected = assert.rejects(first, { name: 'AbortError' })
  leaveFirst()
  const leaveSecond = scope.mount()
  leaveFirst()
  pending.resolve('obsolete')
  await rejected
  const second = await scope.run(async () => 'current')
  let downloads = 0
  applyScopedResult(second, () => {
    downloads += 1
  })
  assert.equal(unwrapScopedResult(second), 'current')
  assert.equal(downloads, 1)
  leaveSecond()
})

test('a resolved result cannot trigger UI effects after its view exits', async () => {
  const scope = createAsyncViewScope()
  const leave = scope.mount()
  const result = await scope.run(async () => 'completed')
  leave()
  let effects = 0
  applyScopedResult(result, () => {
    effects += 1
  })
  assert.equal(effects, 0)
  assert.throws(() => unwrapScopedResult(result), { name: 'AbortError' })
  await assert.rejects(
    scope.run(async () => 'not mounted'),
    { name: 'AbortError' },
  )
})

test('current server failure is preserved for the mounted view', async () => {
  const scope = createAsyncViewScope()
  const leave = scope.mount()
  await assert.rejects(
    scope.run(async () => {
      throw new Error('server failure')
    }),
    /server failure/,
  )
  leave()
})
