import assert from 'node:assert/strict'
import test from 'node:test'

import { createAnalysisJobRunner } from '../src/api/analysis/jobRunner.ts'
import type { AnalysisDetails } from '../src/api/analysis/jobTypes.ts'
import { createAnalysisRequestScopes } from '../src/hooks/analysis/analysisRequestScope.ts'
import { deferredJob, jobDetails, jobTransport, noFile } from './analysisJob.fixtures.ts'

for (const transition of ['history selection', 'reset', 'unmount', 'account boundary']) {
  test(`late accepted upload cannot navigate or update progress after ${transition}`, async () => {
    const requests = createAnalysisRequestScopes()
    const scope = requests.begin(null)
    const accepted = deferredJob<AnalysisDetails>()
    const calls: string[] = []
    const runner = createAnalysisJobRunner({
      ...jobTransport(),
      submit: async (...args) => {
        assert.equal(args[4], scope.signal)
        return accepted.promise
      },
      details: async (id) => {
        calls.push('poll')
        return jobDetails(id)
      },
    })
    const pending = runner.analyze(
      noFile,
      'BFS',
      'AUTO',
      false,
      (status) => calls.push(status),
      (submission) => calls.push(submission.analysisId),
      scope.signal,
    )
    const rejected = assert.rejects(pending, { name: 'AbortError' })
    requests.cancel()
    accepted.resolve(jobDetails('job-a', 'QUEUED'))
    await rejected
    assert.equal(scope.isActive(), false)
    assert.deepEqual(calls, [])
  })
}

test('new upload invalidates prior completion and errors without cancelling the new scope', async () => {
  const requests = createAnalysisRequestScopes()
  const previous = requests.begin(null)
  const current = requests.begin(null)
  assert.equal(previous.signal.aborted, true)
  assert.equal(previous.isActive(), false)
  assert.equal(current.isActive(), true)
  current.analysisId = 'accepted-new-id'
  assert.equal(requests.differsFrom('accepted-new-id'), false)
  assert.equal(requests.differsFrom('history-id'), true)
  requests.cancel()
  assert.equal(current.isActive(), false)
})

test('accepted job remains resumable from history after observation is cancelled', async () => {
  const requests = createAnalysisRequestScopes()
  const scope = requests.begin(null)
  const latePoll = deferredJob<AnalysisDetails>()
  let submissions = 0
  let firstPoll = true
  const navigation: string[] = []
  const runner = createAnalysisJobRunner({
    ...jobTransport(),
    submit: async () => {
      submissions += 1
      return jobDetails('persisted-job', 'QUEUED')
    },
    details: async (id) => {
      if (!firstPoll) return jobDetails(id)
      firstPoll = false
      return latePoll.promise
    },
  })
  const pending = runner.analyze(
    noFile,
    'BFS',
    'AUTO',
    false,
    undefined,
    (submission) => navigation.push(submission.analysisId),
    scope.signal,
  )
  await Promise.resolve()
  const rejected = assert.rejects(pending, { name: 'AbortError' })
  requests.cancel()
  latePoll.resolve(jobDetails('persisted-job'))
  await rejected
  assert.deepEqual(navigation, ['persisted-job'])
  const resumed = await runner.resume('persisted-job')
  assert.equal(resumed.result.analysisId, 'persisted-job')
  assert.equal(submissions, 1)
})

test('active upload reports status, submission and completed result once', async () => {
  const scope = createAnalysisRequestScopes().begin(null)
  const statuses: string[] = []
  const accepted: string[] = []
  const result = await createAnalysisJobRunner(jobTransport()).analyze(
    noFile,
    'BFS',
    'AUTO',
    false,
    (status) => statuses.push(status),
    (submission) => accepted.push(submission.analysisId),
    scope.signal,
  )
  assert.deepEqual(statuses, ['QUEUED', 'COMPLETED'])
  assert.deepEqual(accepted, ['job-a'])
  assert.equal(result.result.analysisId, 'job-a')
  assert.equal(scope.isActive(), true)
})
