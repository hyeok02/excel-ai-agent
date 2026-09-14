import axios, { AxiosError } from 'axios'

/**
 * 서버가 내려준 메시지가 없으면 axios 원문("Network Error" 등)이 그대로 화면에 나온다.
 * 사용자가 실제로 마주치는 연결 실패만 한국어 안내로 바꾼다.
 */
const CONNECTION_ERROR_MESSAGES: Record<string, string> = {
  [AxiosError.ERR_NETWORK]:
    '서버에 연결하지 못했습니다. 백엔드가 실행 중인지 확인해주세요.',
  [AxiosError.ECONNABORTED]:
    '서버 응답이 제한 시간을 넘겼습니다. 잠시 후 다시 시도해주세요.',
  [AxiosError.ETIMEDOUT]:
    '서버 응답이 제한 시간을 넘겼습니다. 잠시 후 다시 시도해주세요.',
}

export const getErrorMessage = (error: unknown) => {
  if (axios.isAxiosError<{ message?: string }>(error)) {
    const serverMessage = error.response?.data?.message
    if (serverMessage) return serverMessage

    const code = error.code
    return (code && CONNECTION_ERROR_MESSAGES[code]) ?? error.message
  }

  return error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
}
