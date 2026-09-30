import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react'

import {
  createUser,
  type CreateUserRequest,
  listUsers,
  type ManagedUser,
  updateUserStatus,
} from '@/api/auth'
import { useAuth } from '@/app/providers/auth-context'
import { getErrorMessage } from '@/utils/apiClient'

const INITIAL_FORM: CreateUserRequest = {
  username: '',
  password: '',
  displayName: '',
  role: 'USER',
}

interface StatusNotice {
  id: number
  kind: 'error' | 'success'
  message: string
}

const useUserManagement = () => {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [form, setForm] = useState<CreateUserRequest>(INITIAL_FORM)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [statusNotice, setStatusNotice] = useState<StatusNotice | null>(null)
  const noticeSequence = useRef(0)

  useEffect(() => {
    const load = async () => {
      try {
        setUsers(await listUsers())
      } catch (loadError) {
        setError(getErrorMessage(loadError))
      } finally {
        setIsLoading(false)
      }
    }
    void load()
  }, [])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setSuccess(null)
    setIsSubmitting(true)
    try {
      const created = await createUser(form)
      setUsers((current) => [created, ...current])
      setForm(INITIAL_FORM)
      setSuccess(`${created.displayName} 계정을 생성했습니다.`)
    } catch (createError) {
      setError(getErrorMessage(createError))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleStatusChange = async (managedUser: ManagedUser, enabled: boolean) => {
    if (managedUser.id === currentUser?.id || updatingUserId !== null) return

    setStatusNotice(null)
    setUpdatingUserId(managedUser.id)
    try {
      const updated = await updateUserStatus(managedUser.id, { enabled })
      setUsers((current) =>
        current.map((user) => (user.id === updated.id ? updated : user)),
      )
      noticeSequence.current += 1
      setStatusNotice({
        id: noticeSequence.current,
        kind: 'success',
        message: `${updated.displayName} 계정을 ${updated.enabled ? '활성화' : '비활성화'}했습니다.`,
      })
    } catch (updateError) {
      noticeSequence.current += 1
      setStatusNotice({
        id: noticeSequence.current,
        kind: 'error',
        message: getErrorMessage(updateError),
      })
    } finally {
      setUpdatingUserId(null)
    }
  }

  const dismissStatusNotice = useCallback((noticeId: number) => {
    setStatusNotice((current) => (current?.id === noticeId ? null : current))
  }, [])

  return {
    currentUserId: currentUser?.id ?? null,
    error,
    form,
    handleStatusChange,
    handleSubmit,
    isLoading,
    isSubmitting,
    setForm,
    dismissStatusNotice,
    statusNotice,
    success,
    updatingUserId,
    users,
  }
}

export default useUserManagement
