import { type FormEvent, useEffect, useState } from 'react'

import {
  createUser,
  type CreateUserRequest,
  listUsers,
  type ManagedUser,
} from '@/api/auth'
import { getErrorMessage } from '@/utils/apiClient'

const INITIAL_FORM: CreateUserRequest = {
  username: '',
  password: '',
  displayName: '',
  role: 'USER',
}

const useUserManagement = () => {
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [form, setForm] = useState<CreateUserRequest>(INITIAL_FORM)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

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

  return {
    error,
    form,
    handleSubmit,
    isLoading,
    isSubmitting,
    setForm,
    success,
    users,
  }
}

export default useUserManagement
