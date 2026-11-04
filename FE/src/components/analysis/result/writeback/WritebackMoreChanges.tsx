import { ChevronDown, ChevronUp } from 'lucide-react'
import { type ReactNode, useRef, useState } from 'react'

import {
  CHANGE_PAGE_SIZE,
  nextShownCount,
} from '@/components/analysis/result/writeback/writebackSelection'

interface Props<T> {
  items: T[]
  render: (item: T) => ReactNode
}

/** 첫 카드 아래의 나머지 변경. 10개씩 펼치고, 펼친 뒤에는 다시 접을 수 있다. */
const WritebackMoreChanges = <T,>({ items, render }: Props<T>) => {
  const [shown, setShown] = useState(0)
  const box = useRef<HTMLDivElement>(null)
  const open = shown > 0
  const left = items.length - shown
  const collapse = () => {
    setShown(0)
    box.current?.scrollIntoView({ block: 'nearest' })
  }
  const button = 'rounded-lg px-3 py-1.5 text-xs font-bold transition hover:bg-slate-100'

  return (
    <div className="mt-3 rounded-2xl border border-slate-200 bg-white p-3" ref={box}>
      <button
        aria-expanded={open}
        className="flex w-full items-center justify-between text-xs font-extrabold text-slate-600"
        onClick={() => (open ? collapse() : setShown(nextShownCount(0, items.length)))}
        type="button"
      >
        {open
          ? `나머지 변경 ${items.length}개 중 ${shown}개 표시`
          : `나머지 변경 ${items.length}개 확인`}
        <ChevronDown
          className={open ? 'rotate-180 transition' : 'transition'}
          size={16}
        />
      </button>
      {open && (
        <>
          <div className="mt-3 space-y-3">{items.slice(0, shown).map(render)}</div>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
            {left > 0 && (
              <button
                className={`${button} text-brand-700`}
                onClick={() => setShown(nextShownCount(shown, items.length))}
                type="button"
              >
                {Math.min(CHANGE_PAGE_SIZE, left)}개 더 보기 (남은 {left}개)
              </button>
            )}
            <button
              className={`${button} flex items-center gap-1 text-slate-600`}
              onClick={collapse}
              type="button"
            >
              <ChevronUp size={14} /> 접기
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default WritebackMoreChanges
