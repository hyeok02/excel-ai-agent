import assert from 'node:assert/strict'
import test from 'node:test'

import { AxiosError } from 'axios'

import { getErrorMessage } from '../src/utils/errorMessage.ts'

const axiosErrorWithCode = (code: string) => new AxiosError('Network Error', code)

const axiosErrorWithResponse = (message: string) =>
  new AxiosError('Request failed', 'ERR_BAD_REQUEST', undefined, undefined, {
    config: {},
    data: { message },
    headers: {},
    status: 400,
    statusText: 'Bad Request',
  } as never)

test('서버가 보낸 메시지가 있으면 그대로 보여준다', () => {
  const error = axiosErrorWithResponse('로그인이 필요합니다.')
  assert.equal(getErrorMessage(error), '로그인이 필요합니다.')
})

test('연결 실패는 axios 원문 대신 한국어로 안내한다', () => {
  const message = getErrorMessage(axiosErrorWithCode(AxiosError.ERR_NETWORK))
  assert.match(message, /서버에 연결하지 못했습니다/)
  assert.doesNotMatch(message, /Network Error/)
})

test('응답 지연은 대기 시간 초과로 안내한다', () => {
  for (const code of [AxiosError.ECONNABORTED, AxiosError.ETIMEDOUT]) {
    assert.match(getErrorMessage(axiosErrorWithCode(code)), /제한 시간을 넘겼습니다/)
  }
})

test('axios가 아닌 오류는 메시지를 그대로 쓴다', () => {
  assert.equal(
    getErrorMessage(new Error('분석 대기 시간이 초과되었습니다.')),
    '분석 대기 시간이 초과되었습니다.',
  )
  assert.equal(getErrorMessage('문자열'), '알 수 없는 오류가 발생했습니다.')
})
