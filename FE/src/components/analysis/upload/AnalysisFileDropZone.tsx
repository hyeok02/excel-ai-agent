import { type ChangeEvent, type DragEvent, useState } from 'react'

import {
  EmptyFilePicker,
  SelectedFile,
} from '@/components/analysis/upload/AnalysisFilePickerStates'
import RestoredFilePicker, {
  type RestoredAnalysisFile,
} from '@/components/analysis/upload/RestoredFilePicker'
import type { AnalysisViewStatus } from '@/hooks/analysis/useWorkbookAnalysis'
import { cn } from '@/utils/cn'

interface AnalysisFileDropZoneProps {
  isPending: boolean
  onClearFile: () => void
  onSelectFile: (file: File) => void
  onStartAnalysis: () => void
  restoredFile: RestoredAnalysisFile | null
  selectedFile: File | null
  status: AnalysisViewStatus
}

const AnalysisFileDropZone = ({
  isPending,
  onClearFile,
  onSelectFile,
  onStartAnalysis,
  restoredFile,
  selectedFile,
  status,
}: AnalysisFileDropZoneProps) => {
  const [isDragging, setIsDragging] = useState(false)

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) onSelectFile(file)
    event.target.value = ''
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    const file = event.dataTransfer.files[0]
    if (file) onSelectFile(file)
  }

  return (
    <div
      className={cn(
        'upload-zone',
        (selectedFile || restoredFile) && 'upload-zone-selected',
        isDragging && 'border-brand-500 bg-brand-50',
        isPending && 'pointer-events-none opacity-70',
      )}
      onDragEnter={(event) => {
        event.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={(event) => {
        event.preventDefault()
        setIsDragging(false)
      }}
      onDragOver={(event) => event.preventDefault()}
      onDrop={handleDrop}
    >
      {selectedFile ? (
        <SelectedFile
          file={selectedFile}
          isPending={isPending}
          onClearFile={onClearFile}
          onFileChange={handleFileChange}
          onStartAnalysis={onStartAnalysis}
          status={status}
        />
      ) : restoredFile ? (
        <RestoredFilePicker
          file={restoredFile}
          isPending={isPending}
          onClearFile={onClearFile}
          onFileChange={handleFileChange}
        />
      ) : (
        <EmptyFilePicker isPending={isPending} onFileChange={handleFileChange} />
      )}
    </div>
  )
}

export default AnalysisFileDropZone
