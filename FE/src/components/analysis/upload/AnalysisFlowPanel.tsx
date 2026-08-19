const ANALYSIS_STEPS = [
  ['1', '파일 업로드 및 검증', '형식과 용량을 확인해요'],
  ['2', '워크북 파싱', '시트와 셀 데이터를 읽어요'],
  ['3', '시트·테이블·차트 영역 탐지', '워크북의 주요 영역을 구분해요'],
  ['4', '수식과 셀 참조 관계 분석', '수식과 연결 구조를 추적해요'],
  ['5', '분석 결과·인사이트 구조화', '분석 결과와 핵심 내용을 정리해요'],
  ['6', '결과 저장 및 화면 표시', '결과를 저장하고 화면에 보여줘요'],
] as const

const AnalysisFlowPanel = () => {
  return (
    <article className="panel flex h-full flex-col p-6">
      <p className="text-xs font-bold tracking-[0.12em] text-slate-400">ANALYSIS FLOW</p>
      <h2 className="mt-2 text-base font-extrabold text-slate-950">분석 진행 과정</h2>
      <ol className="mt-5 flex flex-1 flex-col divide-y divide-slate-100">
        {ANALYSIS_STEPS.map(([step, title, description]) => (
          <li
            className="flex flex-1 items-center gap-3 py-3 first:pt-0 last:pb-0"
            key={step}
          >
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-extrabold text-brand-700">
              {step}
            </span>
            <div>
              <p className="text-sm font-bold text-slate-800">{title}</p>
              <p className="mt-0.5 text-xs leading-5 text-slate-400">{description}</p>
            </div>
          </li>
        ))}
      </ol>
    </article>
  )
}

export default AnalysisFlowPanel
