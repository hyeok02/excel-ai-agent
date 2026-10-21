import assert from 'node:assert/strict'
import test from 'node:test'

import { QueryObserver } from '@tanstack/react-query'

import {
  createSessionQueryClient,
  disposeSessionQueryClient,
} from '../src/app/providers/sessionQueryClient.ts'

const deferred = <T>() => {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((yes) => {
    resolve = yes
  })
  return { promise, resolve }
}

for (const key of [
  ['analysis', 'same-analysis-id'],
  ['analysis-history', ''],
  ['writebacks', 'same-analysis-id'],
]) {
  test(`account B cannot read account A's ${key[0]} cache even with identical keys`, async () => {
    const first = createSessionQueryClient()
    first.setQueryData(key, { owner: 'a', secret: 'private' })
    const oldObserver = new QueryObserver(first, {
      queryKey: key,
      queryFn: async () => ({ owner: 'a' }),
      staleTime: Infinity,
    })
    assert.equal(oldObserver.getCurrentResult().data?.owner, 'a')
    oldObserver.destroy()
    disposeSessionQueryClient(first)

    const second = createSessionQueryClient()
    assert.equal(second.getQueryData(key), undefined)
    let calls = 0
    const current = new QueryObserver(second, {
      queryKey: key,
      queryFn: async () => {
        calls += 1
        return { owner: 'b' }
      },
      staleTime: Infinity,
    })
    assert.equal(current.getCurrentResult().data, undefined)
    const result = await current.refetch()
    assert.equal(result.data?.owner, 'b')
    assert.equal(calls, 1)
    assert.equal(first.getQueryCache().getAll().length, 0)
    current.destroy()
    disposeSessionQueryClient(second)
  })
}

test('logout cancels a deferred query; its late response cannot refill either session', async () => {
  const first = createSessionQueryClient()
  const pending = deferred<string>()
  let aborted = false
  const result = first
    .fetchQuery({
      queryKey: ['analysis', 'pending'],
      queryFn: ({ signal }) => {
        signal.addEventListener('abort', () => {
          aborted = true
        })
        return pending.promise
      },
    })
    .catch(() => undefined)
  disposeSessionQueryClient(first)
  const second = createSessionQueryClient()
  pending.resolve('old private answer')
  await result
  await Promise.resolve()
  assert.equal(aborted, true)
  assert.equal(first.getQueryCache().getAll().length, 0)
  assert.equal(second.getQueryCache().getAll().length, 0)
  disposeSessionQueryClient(second)
})

test('old mutations retain only their disposed client, never the new account cache', async () => {
  const first = createSessionQueryClient()
  const pending = deferred<string>()
  const mutation = first.getMutationCache().build(first, {
    mutationFn: () => pending.promise,
    onSuccess: (value) => first.setQueryData(['writebacks'], value),
  })
  const result = mutation.execute(undefined)
  await Promise.resolve()
  disposeSessionQueryClient(first)
  const second = createSessionQueryClient()
  pending.resolve('old mutation')
  await result
  assert.equal(first.getMutationCache().getAll().length, 0)
  assert.equal(second.getQueryData(['writebacks']), undefined)
  disposeSessionQueryClient(first)
  disposeSessionQueryClient(second)
})
