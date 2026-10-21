import assert from 'node:assert/strict'
import test from 'node:test'

import type { CurrentUser } from '../src/api/auth.ts'
import { nextAuthSession } from '../src/app/providers/authSession.ts'

const user = (id: string): CurrentUser => ({
  id,
  username: id,
  displayName: id,
  email: null,
  role: 'USER',
  authProvider: 'LOCAL',
})

test('an account switch replaces the entire session boundary', () => {
  const initial = { user: null, revision: 0 }
  const first = nextAuthSession(initial, user('a'))
  const second = nextAuthSession(first, user('b'))
  assert.equal(first.revision, 1)
  assert.equal(second.revision, 2)
  assert.equal(second.user?.id, 'b')
})

test('logout and same-account relogin never reuse the old session boundary', () => {
  const original = { user: user('a'), revision: 1 }
  const signedOut = nextAuthSession(original, null, true)
  const relogged = nextAuthSession(signedOut, user('a'), true)
  assert.equal(signedOut.revision, 2)
  assert.equal(relogged.revision, 3)
  assert.equal(nextAuthSession(original, user('a'), true).revision, 2)
})

test('same-user refresh preserves the current screen and in-flight requests', () => {
  const original = { user: user('a'), revision: 5 }
  const refreshed = nextAuthSession(original, { ...user('a'), displayName: 'Updated' })
  assert.equal(refreshed.revision, 5)
  assert.equal(refreshed.user?.displayName, 'Updated')
})

test('session expiry drops the private boundary, repeated anonymous refresh is stable', () => {
  const expired = nextAuthSession({ user: user('a'), revision: 8 }, null)
  assert.equal(expired.revision, 9)
  assert.equal(nextAuthSession(expired, null).revision, 9)
})
