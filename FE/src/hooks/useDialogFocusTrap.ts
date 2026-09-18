import { useEffect, useRef } from 'react'

interface DialogFocusTrapOptions {
  isCloseBlocked: boolean
  onClose: () => void
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'

const useDialogFocusTrap = ({ isCloseBlocked, onClose }: DialogFocusTrapOptions) => {
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeBlockedRef = useRef(isCloseBlocked)

  useEffect(() => {
    closeBlockedRef.current = isCloseBlocked
  }, [isCloseBlocked])

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    const previouslyFocused = document.activeElement as HTMLElement | null
    const dialog = dialogRef.current
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !closeBlockedRef.current) onClose()
      if (event.key !== 'Tab' || !dialog) return
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      )
      if (focusable.length === 0) {
        event.preventDefault()
        dialog.focus()
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    dialog?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)?.focus()
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
      previouslyFocused?.focus()
    }
  }, [onClose])

  return dialogRef
}

export default useDialogFocusTrap
