import { Link } from 'react-router-dom'

import { ROUTES } from '@/constants/navigation'

const NotFoundPage = () => {
  return (
    <div className="grid min-h-[60dvh] place-items-center">
      <div className="text-center">
        <p className="text-sm font-bold text-brand-600">404</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-950">
          페이지를 찾을 수 없습니다.
        </h1>
        <Link className="button-primary mt-6 inline-flex" to={ROUTES.dashboard}>
          홈으로 돌아가기
        </Link>
      </div>
    </div>
  )
}

export default NotFoundPage
