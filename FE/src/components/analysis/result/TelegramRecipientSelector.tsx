import { Check, CheckCircle2, CircleAlert, UsersRound } from 'lucide-react'

import {
  TELEGRAM_SHARE_RECIPIENT_LIMIT,
  type TelegramDeliveryResult,
  type TelegramRecipient,
} from '@/api/telegram'

interface TelegramRecipientSelectorProps {
  deliveries?: TelegramDeliveryResult[]
  disabled: boolean
  onToggle: (recipientId: string) => void
  onToggleAll: () => void
  recipients: TelegramRecipient[]
  selectedIds: Set<string>
}

const TelegramRecipientSelector = ({
  deliveries,
  disabled,
  onToggle,
  onToggleAll,
  recipients,
  selectedIds,
}: TelegramRecipientSelectorProps) => {
  const selectableCount = Math.min(recipients.length, TELEGRAM_SHARE_RECIPIENT_LIMIT)
  const allSelected = selectableCount > 0 && selectedIds.size === selectableCount
  const deliveryFor = (id: string) =>
    deliveries?.find((delivery) => delivery.recipientId === id)

  return (
    <>
      <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-6 py-3.5">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-500">
          <UsersRound className="text-brand-500" size={15} />
          연결된 수신자 {recipients.length}명
          {recipients.length > TELEGRAM_SHARE_RECIPIENT_LIMIT && (
            <span className="font-medium text-slate-400">
              · 한 번에 최대 {TELEGRAM_SHARE_RECIPIENT_LIMIT}명
            </span>
          )}
        </div>
        <button
          className="rounded-lg px-2.5 py-1.5 text-xs font-extrabold text-brand-600 transition hover:bg-brand-50"
          disabled={disabled}
          onClick={onToggleAll}
          type="button"
        >
          {allSelected ? '전체 해제' : '전체 선택'}
        </button>
      </div>

      <div className="divide-y divide-slate-100 px-3 py-2">
        {recipients.map((recipient) => {
          const checked = selectedIds.has(recipient.id)
          const selectionLocked =
            !checked && selectedIds.size >= TELEGRAM_SHARE_RECIPIENT_LIMIT
          const delivery = deliveryFor(recipient.id)
          return (
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-xl px-3 py-3.5 transition ${
                checked ? 'bg-brand-50/70' : 'hover:bg-slate-50'
              } ${selectionLocked ? 'cursor-not-allowed' : ''}`}
              key={recipient.id}
            >
              <input
                checked={checked}
                className="peer sr-only"
                disabled={disabled || selectionLocked}
                onChange={() => onToggle(recipient.id)}
                type="checkbox"
              />
              <span
                className={`grid size-5 shrink-0 place-items-center rounded-md border transition peer-focus-visible:ring-2 peer-focus-visible:ring-brand-500 peer-focus-visible:ring-offset-2 ${
                  checked
                    ? 'border-brand-600 bg-brand-600 text-white'
                    : 'border-slate-300 bg-white text-transparent'
                }`}
              >
                <Check size={13} strokeWidth={3} />
              </span>
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white text-sm font-extrabold text-brand-700 shadow-sm ring-1 ring-slate-100">
                {recipient.displayName.slice(0, 1).toUpperCase()}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-extrabold text-slate-800">
                  {recipient.displayName}
                </span>
                <span className="mt-0.5 block truncate text-xs text-slate-400">
                  {recipient.username ? `@${recipient.username}` : '텔레그램 수신자'}
                </span>
              </span>
              {delivery && <DeliveryBadge delivery={delivery} />}
            </label>
          )
        })}
      </div>
    </>
  )
}

const DeliveryBadge = ({ delivery }: { delivery: TelegramDeliveryResult }) => (
  <span
    className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.68rem] font-extrabold ${
      delivery.success ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
    }`}
    title={delivery.errorMessage ?? undefined}
  >
    {delivery.success ? <CheckCircle2 size={13} /> : <CircleAlert size={13} />}
    {delivery.success ? '전송 완료' : '전송 실패'}
  </span>
)

export default TelegramRecipientSelector
