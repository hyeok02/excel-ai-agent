const AnalysisPage = () => {
  return (
    <div className="space-y-6">
      <section>
        <p className="eyebrow">EXCEL ANALYSIS</p>
        <h1 className="page-title">엑셀분석</h1>
        <p className="page-description">
          엑셀 파일을 업로드하면 시트별 리전(테이블, 차트, 셀)을 자동으로 탐지하고, 수식과
          데이터를 구조화하여 화면에 표시합니다.
        </p>
      </section>

      <section className="panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5">
          <div>
            <h2 className="section-title">파일 업로드</h2>
          </div>
          <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
            Step 1
          </span>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="mr-2 text-sm font-semibold text-slate-700">분석 모드</span>
          <button className="mode-button mode-button-active" type="button">
            BFS 군집화
          </button>
          <button className="mode-button" type="button">
            LLM 직접 분석
          </button>
        </div>

        <label className="mt-5 flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-brand-300 bg-brand-50/40 p-8 text-center transition hover:border-brand-500 hover:bg-brand-50">
          <span className="grid size-14 place-items-center rounded-2xl bg-white text-sm font-bold text-brand-700 shadow-sm">
            XLS
          </span>
          <span className="mt-4 font-semibold text-slate-800">
            Excel 파일을 끌어놓거나 클릭하세요
          </span>
          <span className="mt-1 text-sm text-slate-500">
            .xlsx, .xlsm (최대 50MB) — BFS 알고리즘 기반 분석
          </span>
          <input accept=".xlsx,.xlsm" className="sr-only" type="file" />
        </label>
      </section>
    </div>
  )
}

export default AnalysisPage
