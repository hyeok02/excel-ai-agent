const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
const ALLOWED_EXTENSIONS = ['xlsx', 'xlsm']

export const formatBytes = (bytes: number) => {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export const validateAnalysisFile = (file: File) => {
  const extension = file.name.split('.').pop()?.toLowerCase()

  if (!extension || !ALLOWED_EXTENSIONS.includes(extension)) {
    return '.xlsx 또는 .xlsm 형식의 Excel 파일만 업로드할 수 있습니다.'
  }

  if (file.size === 0) {
    return '빈 파일은 업로드할 수 없습니다.'
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return '파일 크기는 50MB를 초과할 수 없습니다.'
  }

  return null
}
