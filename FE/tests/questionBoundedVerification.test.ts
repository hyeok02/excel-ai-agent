import assert from 'node:assert/strict'
import test from 'node:test'

import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

for (const check of [
  'semantic_alias_resolved',
  'premise_not_confirmed',
  'category_match_interpreted',
]) {
  test(`${check} cannot become green even with stale request-wide metadata`, () => {
    const answer = questionAnswer({
      verification: {
        level: 'request_checked',
        checks: ['table_scope', 'metric', 'source_cells', check],
      },
    })
    assert.equal(questionVerificationPresentation(answer).tone, 'limited')
    answer.verification!.level = 'unverified'
    assert.equal(questionVerificationPresentation(answer).tone, 'neutral')
    answer.status = 'insufficient_evidence'
    assert.equal(questionVerificationPresentation(answer).tone, 'neutral')
  })
}
