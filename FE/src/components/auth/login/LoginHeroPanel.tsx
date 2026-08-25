import { Sparkles } from 'lucide-react'

const BENEFITS = ['근거 기반 분석', '역할 기반 보안', '통합 업무 기록']

const LoginHeroPanel = () => (
  <section className="relative hidden min-w-0 px-[clamp(4rem,7vw,8rem)] py-14 text-white lg:flex lg:flex-col lg:justify-between xl:py-16">
    <div className="auth-reveal auth-reveal-delay-1 flex items-center gap-3">
      <span className="grid size-11 place-items-center rounded-[0.9rem] border border-white/15 bg-white/10 text-blue-100 shadow-lg backdrop-blur">
        <Sparkles size={20} strokeWidth={2.1} />
      </span>
      <div>
        <p className="text-[1.05rem] font-extrabold tracking-[-0.025em]">
          Decision Support
        </p>
        <p className="mt-1 text-[0.7rem] font-bold tracking-[0.18em] text-blue-200/75">
          AI WORKSPACE
        </p>
      </div>
    </div>

    <div className="auth-reveal auth-reveal-delay-2 max-w-[38rem] pb-6 xl:pb-10">
      <div className="flex items-center gap-3 text-[0.72rem] font-bold tracking-[0.16em] text-blue-200">
        <span className="h-px w-8 bg-blue-300/70" />
        DECISION INTELLIGENCE
      </div>
      <h1 className="mt-7 text-[2.75rem] font-extrabold leading-[1.14] tracking-[-0.05em] xl:text-[3.15rem] 2xl:text-[3.45rem]">
        복잡한 데이터에서
        <br />
        명확한 판단까지.
      </h1>
      <p className="mt-6 max-w-[35rem] text-[1.1rem] leading-8 text-blue-50/85">
        <span className="block">사내 데이터와 AI Agent를 안전하게 연결하고,</span>
        <span className="block">
          복잡한 Excel 구조를 근거 있는 인사이트로 전환합니다.
        </span>
      </p>

      <div className="mt-9 flex flex-wrap gap-2.5">
        {BENEFITS.map((item) => (
          <span
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.055] px-3.5 py-2 text-[0.78rem] font-semibold text-blue-50 backdrop-blur"
            key={item}
          >
            <span className="size-1.5 rounded-full bg-blue-300" />
            {item}
          </span>
        ))}
      </div>
    </div>

    <p className="auth-reveal auth-reveal-delay-3 text-[1.1rem] font-normal leading-8 tracking-[-0.015em] text-blue-100/45">
      Secure internal access · Decision Support System
    </p>
  </section>
)

export default LoginHeroPanel
