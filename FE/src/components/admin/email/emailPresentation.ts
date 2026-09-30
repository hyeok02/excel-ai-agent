const DATE_FORMATTER = new Intl.DateTimeFormat('ko-KR', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export const formatEmailDate = (value: string) => DATE_FORMATTER.format(new Date(value))
