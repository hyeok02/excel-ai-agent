import axios from 'axios'
import { Link2Off, LoaderCircle, RefreshCw, WifiOff } from 'lucide-react'

export const PublicShareLoadingState = () => (
  <section aria-live="polite" className="panel grid min-h-[28rem] place-items-center p-8">
    <div className="text-center">
      <LoaderCircle
        aria-hidden="true"
        className="mx-auto animate-spin text-brand-600"
        size={30}
      />
      <p className="mt-4 text-sm font-bold text-slate-700">
        공유 결과를 불러오고 있습니다.
      </p>
    </div>
  </section>
)

export const PublicShareErrorState = ({
  error,
  onRetry,
}: {
  error: unknown
  onRetry: () => void
}) => {
  const unavailable = axios.isAxiosError(error) && error.response?.status === 404
  const Icon = unavailable ? Link2Off : WifiOff

  return (
    <section className="panel grid min-h-[28rem] place-items-center p-8 text-center">
      <div className="max-w-md">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-slate-100 text-slate-500">
          <Icon aria-hidden="true" size={25} />
        </span>
        <h1 className="mt-5 text-xl font-extrabold tracking-tight text-slate-950">
          {unavailable
            ? '공유 링크를 사용할 수 없습니다'
            : '공유 결과를 불러오지 못했습니다'}
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          {unavailable
            ? '링크가 만료 또는 해제되었거나 주소가 올바르지 않습니다. 메시지를 보낸 담당자에게 새 링크를 요청해 주세요.'
            : '네트워크 또는 서버 연결을 확인한 뒤 다시 시도해 주세요.'}
        </p>
        {!unavailable && (
          <button
            className="button-primary mt-5 inline-flex gap-2"
            onClick={onRetry}
            type="button"
          >
            <RefreshCw size={15} /> 다시 불러오기
          </button>
        )}
      </div>
    </section>
  )
}
