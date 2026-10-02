import { EyeOff } from 'lucide-react'

interface HiddenSheetToggleProps {
  includeHiddenSheets: boolean
  isPending: boolean
  onChange: (includeHiddenSheets: boolean) => void
}

/**
 * 숨김 시트 포함 여부를 고르는 스위치.
 *
 * 기본값은 '제외'다. 숨겨 둔 시트는 대부분 중간 계산이나 옛 자료라서
 * 결과를 어지럽히지만, 숨긴 시트에 원본이 들어 있는 파일도 있어서
 * 사용자가 직접 켤 수 있어야 한다.
 */
const HiddenSheetToggle = ({
  includeHiddenSheets,
  isPending,
  onChange,
}: HiddenSheetToggleProps) => (
  <fieldset className="flex w-full items-center gap-3 border-t border-slate-200/70 pt-2.5">
    <legend className="sr-only">숨김 시트</legend>
    <label className="flex cursor-pointer items-center gap-2 pl-1 text-xs font-extrabold text-slate-500">
      <input
        checked={includeHiddenSheets}
        className="h-3.5 w-3.5 accent-brand-600"
        disabled={isPending}
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <EyeOff aria-hidden="true" size={13} />
      숨김 시트도 분석
    </label>
    <p className="min-w-0 text-xs text-slate-400">
      {includeHiddenSheets
        ? '숨겨 둔 시트까지 함께 읽습니다. 중간 계산 시트가 결과에 섞일 수 있어요.'
        : '숨겨 둔 시트는 건너뜁니다. 숨긴 시트에 원본이 있으면 켜주세요.'}
    </p>
  </fieldset>
)

export default HiddenSheetToggle
