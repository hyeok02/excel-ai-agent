import { useEffect } from 'react'

export const usePublicShareMetadata = () => {
  useEffect(() => {
    const previousTitle = document.title
    document.title = 'Excel 분석 공유 보고서'

    const managed: HTMLMetaElement[] = []
    const addMeta = (name: string, content: string) => {
      const meta = document.createElement('meta')
      meta.name = name
      meta.content = content
      meta.dataset.publicShare = 'true'
      document.head.appendChild(meta)
      managed.push(meta)
    }
    addMeta('robots', 'noindex, nofollow, noarchive')
    addMeta('referrer', 'no-referrer')

    return () => {
      document.title = previousTitle
      managed.forEach((meta) => meta.remove())
    }
  }, [])
}
