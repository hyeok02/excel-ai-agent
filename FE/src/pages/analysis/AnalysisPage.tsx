const AnalysisPage = () => {
  return (
    <div className="space-y-7">
      <section className="panel page-heading p-6 md:p-8">
        <div>
          <p className="eyebrow">EXCEL INTELLIGENCE</p>
          <h1 className="page-title">Excel 분석</h1>
          <p className="page-description">
            엑셀 파일을 업로드하면 시트별 리전(테이블, 차트, 셀)을 자동으로 탐지하고,
            수식과 데이터를 구조화하여 화면에 표시합니다.
          </p>
        </div>
        <span className="status-pill">
          <span />
          분석 엔진 준비 중
        </span>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <article className="panel p-5 md:p-7">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-extrabold tracking-tight text-slate-950">
                분석할 파일을 선택하세요
              </h2>
              <p className="mt-2 text-sm text-slate-500">
                파일은 안전하게 저장되며 분석 이력에서 다시 확인할 수 있어요.
              </p>
            </div>
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-2 rounded-2xl bg-slate-50 p-2">
            <span className="mr-2 pl-2 text-sm font-bold text-slate-700">분석 모드</span>
            <button className="mode-button mode-button-active" type="button">
              BFS 군집화
            </button>
            <button className="mode-button" type="button">
              LLM 직접 분석
            </button>
          </div>

          <label className="upload-zone">
            <span className="upload-icon">XLSX</span>
            <span className="mt-5 text-base font-bold text-slate-900">
              Excel 파일을 끌어놓거나 클릭하세요
            </span>
            <span className="mt-2 text-sm text-slate-500">
              .xlsx, .xlsm 형식 · 파일당 최대 50MB
            </span>
            <span className="mt-5 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white shadow-brand">
              파일 찾아보기
            </span>
            <input accept=".xlsx,.xlsm" className="sr-only" type="file" />
          </label>
        </article>

        <aside>
          <article className="panel flex h-full flex-col p-6">
            <p className="text-xs font-bold tracking-[0.12em] text-slate-400">
              ANALYSIS FLOW
            </p>
            <h2 className="mt-2 text-base font-extrabold text-slate-950">
              분석 진행 과정
            </h2>
            <ol className="mt-5 flex flex-1 flex-col divide-y divide-slate-100">
              {[
                ['1', '파일 업로드 및 검증', '형식과 용량을 확인해요'],
                ['2', '워크북 파싱', '시트와 셀 데이터를 읽어요'],
                ['3', '시트·테이블·차트 영역 탐지', '워크북의 주요 영역을 구분해요'],
                ['4', '수식과 셀 참조 관계 분석', '수식과 연결 구조를 추적해요'],
                ['5', 'AI 인사이트 생성', '분석 결과와 핵심 내용을 정리해요'],
                ['6', '결과 저장 및 화면 표시', '결과를 저장하고 화면에 보여줘요'],
              ].map(([step, title, description]) => (
                <li
                  className="flex flex-1 items-center gap-3 py-3 first:pt-0 last:pb-0"
                  key={step}
                >
                  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-extrabold text-brand-700">
                    {step}
                  </span>
                  <div>
                    <p className="text-sm font-bold text-slate-800">{title}</p>
                    <p className="mt-0.5 text-xs leading-5 text-slate-400">
                      {description}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </article>
        </aside>
      </section>
    </div>
  )
}

export default AnalysisPage
