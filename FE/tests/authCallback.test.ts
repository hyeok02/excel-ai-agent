import assert from 'node:assert/strict'
import test from 'node:test'

import { startAuthCallback } from '../src/pages/auth/callback/authCallback.ts'
import { deferredJob } from './analysisJob.fixtures.ts'

const options = (refresh: () => Promise<unknown>, events: string[]) => ({
  hasError: false,
  refresh,
  onSuccess: () => {
    events.push('success')
  },
  onErrorRedirect: () => {
    events.push('provider-error')
  },
  onFailure: () => {
    events.push('failure')
  },
  onRetry: () => {
    events.push('login')
  },
})

test('superseded StrictMode callback cannot redirect after the active callback succeeds', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const old = deferredJob<unknown>()
  const current = deferredJob<unknown>()
  const events: string[] = []
  const leaveOld = startAuthCallback(options(() => old.promise, events))
  leaveOld()
  const leaveCurrent = startAuthCallback(options(() => current.promise, events))
  current.resolve({ id: 'user' })
  old.resolve(null)
  await Promise.resolve()
  t.mock.timers.tick(1500)
  assert.deepEqual(events, ['success'])
  leaveCurrent()
})

test('unmount clears a scheduled authentication failure redirect', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const events: string[] = []
  const leave = startAuthCallback(options(async () => null, events))
  await Promise.resolve()
  assert.deepEqual(events, ['failure'])
  leave()
  t.mock.timers.tick(1500)
  assert.deepEqual(events, ['failure'])
})

test('active authentication failure still returns to login after its delay', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const events: string[] = []
  const leave = startAuthCallback(options(async () => null, events))
  await Promise.resolve()
  t.mock.timers.tick(1500)
  assert.deepEqual(events, ['failure', 'login'])
  leave()
})

test('provider error navigates without an unnecessary refresh', () => {
  const events: string[] = []
  const leave = startAuthCallback({
    ...options(async () => {
      throw new Error('must not refresh')
    }, events),
    hasError: true,
  })
  assert.deepEqual(events, ['provider-error'])
  leave()
})
