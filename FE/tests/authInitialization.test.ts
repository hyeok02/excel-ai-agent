import assert from 'node:assert/strict'
import test from 'node:test'

import { initializeAuthSession } from '../src/app/providers/authInitialization.ts'

const deferred = <T>() => {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((yes) => {
    resolve = yes
  })
  return { promise, resolve }
}

const harness = () => {
  const configuration = deferred<string>()
  const identity = deferred<string | null>()
  let mounted = true
  let current = true
  const effects: string[] = []
  const options = {
    config: () => configuration.promise,
    csrf: async () => undefined,
    user: () => {
      effects.push('user-request')
      return identity.promise
    },
    isMounted: () => mounted,
    isCurrent: () => current,
    onConfig: () => effects.push('config'),
    onUser: (user: string | null) => effects.push(`user:${user}`),
    onSettled: () => effects.push('settled'),
  }
  return {
    configuration,
    identity,
    effects,
    options,
    unmount: () => {
      mounted = false
    },
    supersede: () => {
      current = false
    },
  }
}

test('delayed bootstrap does not issue a new identity request after login begins', async () => {
  const state = harness()
  const pending = initializeAuthSession(state.options)
  state.supersede()
  state.configuration.resolve('public-config')
  await pending
  assert.deepEqual(state.effects, ['config', 'settled'])
})

test('obsolete StrictMode initialization cannot commit config, identity or loading', async () => {
  const state = harness()
  const pending = initializeAuthSession(state.options)
  state.unmount()
  state.configuration.resolve('config')
  await pending
  assert.deepEqual(state.effects, [])
})

test('identity response from before login cannot overwrite the current account', async () => {
  const state = harness()
  const pending = initializeAuthSession(state.options)
  state.configuration.resolve('config')
  await new Promise<void>((resolve) => setImmediate(resolve))
  assert.equal(state.effects.includes('user-request'), true)
  state.supersede()
  state.identity.resolve('old-owner')
  await pending
  assert.equal(state.effects.includes('user:old-owner'), false)
})

test('current bootstrap restores the account and settles normally', async () => {
  const state = harness()
  const pending = initializeAuthSession(state.options)
  state.configuration.resolve('config')
  state.identity.resolve('owner')
  await pending
  assert.deepEqual(state.effects, ['config', 'user-request', 'user:owner', 'settled'])
})

test('current identity failure settles as unauthenticated', async () => {
  const state = harness()
  state.options.user = async () => {
    throw new Error('offline')
  }
  const pending = initializeAuthSession(state.options)
  state.configuration.resolve('config')
  await pending
  assert.deepEqual(state.effects, ['config', 'user:null', 'settled'])
})
