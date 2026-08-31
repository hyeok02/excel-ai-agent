import { ArrowRight, Bot, Braces, CheckCircle2, Sparkles } from 'lucide-react'

interface AgentReadySectionProps {
  hasInsightReport: boolean
}

const AgentReadySection = ({ hasInsightReport }: AgentReadySectionProps) => {
  const items = [
    {
      icon: Braces,
      step: '01',
      title: '구조화 완료',
      description:
        '시트·영역·셀·수식·차트 정보가 JSON/YAML로 다시 사용할 수 있게 정리됐어요.',
    },
    {
      icon: Bot,
      step: '02',
      title: hasInsightReport ? 'AI 검토 완료' : 'AI Agent 연결 가능',
      description: hasInsightReport
        ? 'AI가 만든 주장과 원본 셀 근거를 대조해 검증된 결과만 표시했어요.'
        : '내보낸 구조화 결과를 사내 질의응답·검토·보고서 Agent의 입력으로 사용할 수 있어요.',
    },
    {
      icon: CheckCircle2,
      step: '03',
      title: '추적 가능한 근거',
      description: '결과마다 시트와 셀 범위를 남겨 원본 Excel에서 다시 확인할 수 있어요.',
    },
  ]

  return (
    <section className="relative mt-6 overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-cyan-50/70 p-5 md:p-7">
      <span className="pointer-events-none absolute -right-20 -top-24 size-64 rounded-full border border-brand-200/60" />
      <span className="pointer-events-none absolute -bottom-24 right-32 size-52 rounded-full bg-brand-100/35 blur-sm" />

      <div className="relative flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-brand-700">
            <Sparkles aria-hidden="true" size={17} />
            <p className="text-xs font-extrabold tracking-[0.16em]">AGENT READY DATA</p>
          </div>
          <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">
            분석 결과를 다음 업무에 연결할 수 있어요
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            화면용 요약을 넘어, 다른 AI Agent가 읽을 수 있는 구조화 데이터와 원본 근거를
            함께 보존합니다.
          </p>
        </div>
        <span className="rounded-full border border-brand-200 bg-white/80 px-3 py-1.5 text-xs font-extrabold text-brand-700 shadow-sm backdrop-blur">
          NEXT WORKFLOW READY
        </span>
      </div>

      <div className="relative mt-6 grid gap-3 lg:grid-cols-3">
        {items.map(({ icon: Icon, step, title, description }, index) => (
          <div className="relative" key={title}>
            <article className="h-full rounded-2xl border border-white bg-white/85 p-5 shadow-[0_14px_35px_rgb(37_99_235/10%)] backdrop-blur transition duration-200 hover:-translate-y-1 hover:border-brand-200 hover:shadow-[0_18px_40px_rgb(37_99_235/15%)]">
              <div className="flex items-center justify-between">
                <span className="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-600 ring-1 ring-brand-100">
                  <Icon aria-hidden="true" size={19} />
                </span>
                <span className="text-xs font-black tracking-[0.14em] text-brand-200">
                  {step}
                </span>
              </div>
              <h3 className="mt-4 text-base font-extrabold text-slate-900">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
            </article>
            {index < items.length - 1 && (
              <span className="absolute -right-5 top-1/2 z-10 hidden size-7 -translate-y-1/2 place-items-center rounded-full border border-brand-100 bg-white text-brand-500 shadow-sm lg:grid">
                <ArrowRight aria-hidden="true" size={14} />
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

export default AgentReadySection
