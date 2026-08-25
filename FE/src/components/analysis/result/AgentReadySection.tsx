import { Bot, Braces, CheckCircle2 } from 'lucide-react'

interface AgentReadySectionProps {
  hasInsightReport: boolean
}

const AgentReadySection = ({ hasInsightReport }: AgentReadySectionProps) => {
  const items = [
    {
      icon: Braces,
      title: '구조화 완료',
      description:
        '시트·영역·셀·수식·차트 정보가 JSON/YAML로 다시 사용할 수 있게 정리됐어요.',
    },
    {
      icon: Bot,
      title: hasInsightReport ? 'AI 검토 완료' : 'AI Agent 연결 가능',
      description: hasInsightReport
        ? '구조화된 근거를 바탕으로 AI가 요약, 위험 요소와 검토 권고를 생성했어요.'
        : '내보낸 구조화 결과를 사내 질의응답·검토·보고서 Agent의 입력으로 사용할 수 있어요.',
    },
    {
      icon: CheckCircle2,
      title: '추적 가능한 근거',
      description: '결과마다 시트와 셀 범위를 남겨 원본 Excel에서 다시 확인할 수 있어요.',
    },
  ]

  return (
    <section className="mt-6 rounded-2xl bg-slate-950 p-5 text-white md:p-6">
      <p className="text-xs font-extrabold tracking-[0.16em] text-blue-300">
        AGENT READY DATA
      </p>
      <h2 className="mt-2 text-lg font-extrabold">
        분석 결과를 다음 업무에 연결할 수 있어요
      </h2>
      <p className="mt-1 max-w-3xl text-xs leading-6 text-slate-400">
        화면용 요약만 만든 것이 아니라, 다른 AI Agent가 읽을 수 있는 구조화 데이터와 원본
        근거를 함께 보존합니다.
      </p>
      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        {items.map(({ icon: Icon, title, description }) => (
          <div className="rounded-2xl bg-white/7 p-4 ring-1 ring-white/10" key={title}>
            <Icon aria-hidden="true" className="text-blue-300" size={18} />
            <h3 className="mt-3 text-sm font-extrabold">{title}</h3>
            <p className="mt-1.5 text-xs leading-5 text-slate-400">{description}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

export default AgentReadySection
