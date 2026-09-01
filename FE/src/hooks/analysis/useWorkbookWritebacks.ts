import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  approveWorkbookWriteback,
  downloadWorkbookWriteback,
  getWorkbookWritebacks,
  proposeWorkbookWriteback,
  rejectWorkbookWriteback,
} from '@/api/analysis'
import { getErrorMessage } from '@/utils/apiClient'

export const useWorkbookWritebacks = (analysisId: string) => {
  const queryClient = useQueryClient()
  const key = ['workbook-writebacks', analysisId]
  const history = useQuery({
    queryKey: key,
    queryFn: () => getWorkbookWritebacks(analysisId),
  })
  const refresh = () => queryClient.invalidateQueries({ queryKey: key })

  const proposal = useMutation({
    mutationFn: (instruction: string) =>
      proposeWorkbookWriteback(analysisId, instruction),
    onSuccess: refresh,
  })
  const approval = useMutation({
    mutationFn: (writebackId: string) =>
      approveWorkbookWriteback(analysisId, writebackId),
    onSuccess: refresh,
  })
  const rejection = useMutation({
    mutationFn: (writebackId: string) => rejectWorkbookWriteback(analysisId, writebackId),
    onSuccess: refresh,
  })
  const download = useMutation({
    mutationFn: (writebackId: string) =>
      downloadWorkbookWriteback(analysisId, writebackId),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    },
  })

  const resetMutationMessages = () => {
    proposal.reset()
    approval.reset()
    rejection.reset()
    download.reset()
  }

  const propose = async (instruction: string) => {
    resetMutationMessages()
    return proposal.mutateAsync(instruction)
  }

  const approve = async (writebackId: string) => {
    resetMutationMessages()
    return approval.mutateAsync(writebackId)
  }

  const reject = async (writebackId: string) => {
    resetMutationMessages()
    return rejection.mutateAsync(writebackId)
  }

  const downloadFile = (writebackId: string) => {
    resetMutationMessages()
    download.mutate(writebackId)
  }

  const error =
    proposal.error ?? approval.error ?? rejection.error ?? download.error ?? history.error
  const pendingAction: 'approve' | 'reject' | 'download' | null = approval.isPending
    ? 'approve'
    : rejection.isPending
      ? 'reject'
      : download.isPending
        ? 'download'
        : null
  return {
    items: history.data ?? [],
    propose,
    approve,
    reject,
    download: downloadFile,
    isLoading: history.isLoading,
    isProposing: proposal.isPending,
    pendingId: approval.isPending
      ? approval.variables
      : rejection.isPending
        ? rejection.variables
        : download.isPending
          ? download.variables
          : null,
    pendingAction,
    downloadNotice:
      download.isSuccess && download.variables
        ? { writebackId: download.variables, filename: download.data.filename }
        : null,
    errorMessage: error ? getErrorMessage(error) : null,
  }
}
