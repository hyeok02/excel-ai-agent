import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  approveWorkbookWriteback,
  downloadWorkbookWriteback,
  getWorkbookWritebacks,
  proposeWorkbookWriteback,
  rejectWorkbookWriteback,
} from '@/api/analysis'
import { applyScopedResult, unwrapScopedResult } from '@/hooks/asyncViewScope'
import { useAsyncViewScope } from '@/hooks/useAsyncViewScope'
import { getErrorMessage } from '@/utils/apiClient'

export const useWorkbookWritebacks = (analysisId: string) => {
  const queryClient = useQueryClient()
  const scope = useAsyncViewScope()
  const key = ['workbook-writebacks', analysisId]
  const history = useQuery({
    queryKey: key,
    queryFn: () => getWorkbookWritebacks(analysisId),
  })
  const refresh = () => queryClient.invalidateQueries({ queryKey: key })

  const proposal = useMutation({
    mutationFn: (instruction: string) =>
      scope.run(() => proposeWorkbookWriteback(analysisId, instruction)),
    onSuccess: (result) => applyScopedResult(result, refresh),
  })
  const approval = useMutation({
    mutationFn: ({
      writebackId,
      approvedCells,
    }: {
      writebackId: string
      approvedCells: string[]
    }) =>
      scope.run(() => approveWorkbookWriteback(analysisId, writebackId, approvedCells)),
    onSuccess: (result) => applyScopedResult(result, refresh),
  })
  const rejection = useMutation({
    mutationFn: (writebackId: string) =>
      scope.run(() => rejectWorkbookWriteback(analysisId, writebackId)),
    onSuccess: (result) => applyScopedResult(result, refresh),
  })
  const download = useMutation({
    mutationFn: (writebackId: string) =>
      scope.run(() => downloadWorkbookWriteback(analysisId, writebackId)),
    onSuccess: (result) =>
      applyScopedResult(result, ({ blob, filename }) => {
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.setTimeout(() => URL.revokeObjectURL(url), 0)
      }),
  })

  const resetMutationMessages = () => {
    proposal.reset()
    approval.reset()
    rejection.reset()
    download.reset()
  }

  const propose = async (instruction: string) => {
    resetMutationMessages()
    return unwrapScopedResult(await proposal.mutateAsync(instruction))
  }

  const approve = async (writebackId: string, approvedCells: string[] = []) => {
    resetMutationMessages()
    return unwrapScopedResult(await approval.mutateAsync({ approvedCells, writebackId }))
  }

  const reject = async (writebackId: string) => {
    resetMutationMessages()
    return unwrapScopedResult(await rejection.mutateAsync(writebackId))
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
      ? approval.variables.writebackId
      : rejection.isPending
        ? rejection.variables
        : download.isPending
          ? download.variables
          : null,
    pendingAction,
    downloadNotice:
      download.isSuccess && download.variables
        ? { writebackId: download.variables, filename: download.data.value.filename }
        : null,
    errorMessage: error ? getErrorMessage(error) : null,
  }
}
