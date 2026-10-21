import assert from 'node:assert/strict'
import test from 'node:test'

import { QueryClient, QueryObserver } from '@tanstack/react-query'

import {
  createAnalysisJobRunner,
  waitForAnalysisPoll,
} from '../src/api/analysis/jobRunner.ts'
import type {
  AnalysisDetails,
  AnalysisResultDetails,
} from '../src/api/analysis/jobTypes.ts'
import {
  deferredJob,
  jobDetails,
  jobResult,
  jobTransport,
} from './analysisJob.fixtures.ts'

test('switching restored analysis cancels old polling and only publishes new progress', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const late = deferredJob<AnalysisDetails>()
  const progress: string[] = []
  let oldSignal: AbortSignal | undefined
  let results = 0
  const runner = createAnalysisJobRunner({
    ...jobTransport(),
    details: async (id, signal) => {
      if (id === 'old') {
        oldSignal = signal
        return late.promise
      }
      return jobDetails(id)
    },
    result: async (id) => {
      results += 1
      return jobResult(id)
    },
  })
  const options = (id: string) => ({
    queryKey: ['analysis', id],
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      runner.resume(id, (status) => progress.push(`${id}:${status}`), signal),
  })
  const observer = new QueryObserver(client, options('old'))
  const unsubscribe = observer.subscribe(() => {})
  observer.setOptions(options('new'))
  assert.equal(oldSignal?.aborted, true)
  late.resolve(jobDetails('old'))
  await client.fetchQuery(options('new'))
  assert.deepEqual(progress, ['new:COMPLETED'])
  assert.equal(results, 1)
  assert.equal(observer.getCurrentResult().data?.result.analysisId, 'new')
  unsubscribe()
  client.clear()
})

test('unmount aborts the restored result request even if transport resolves late', async () => {
  const client = new QueryClient()
  const late = deferredJob<AnalysisResultDetails>()
  const enteredResult = deferredJob<void>()
  let resultSignal: AbortSignal | undefined
  const runner = createAnalysisJobRunner({
    ...jobTransport(),
    result: async (_, signal) => {
      resultSignal = signal
      enteredResult.resolve()
      return late.promise
    },
  })
  const observer = new QueryObserver(client, {
    queryKey: ['analysis', 'old'],
    queryFn: ({ signal }) => runner.resume('old', undefined, signal),
  })
  const unsubscribe = observer.subscribe(() => {})
  await enteredResult.promise
  unsubscribe()
  assert.equal(resultSignal?.aborted, true)
  late.resolve(jobResult('old'))
  await new Promise((resolve) => setTimeout(resolve, 0))
  assert.equal(client.getQueryData(['analysis', 'old']), undefined)
  client.clear()
})

test('polling delay aborts immediately instead of leaving another request queued', async () => {
  const controller = new AbortController()
  const pending = waitForAnalysisPoll(60_000, controller.signal)
  const rejected = assert.rejects(pending, { name: 'AbortError' })
  controller.abort()
  await rejected
  await assert.rejects(waitForAnalysisPoll(60_000, controller.signal), {
    name: 'AbortError',
  })
})

test('genuine server failure still rejects without requesting the result', async () => {
  let resultRequests = 0
  const runner = createAnalysisJobRunner({
    ...jobTransport(),
    details: async (id) => ({
      ...jobDetails(id, 'FAILED'),
      failureMessage: 'server failure',
    }),
    result: async (id) => {
      resultRequests += 1
      return jobResult(id)
    },
  })
  await assert.rejects(runner.resume('failed'), /server failure/)
  assert.equal(resultRequests, 0)
})
