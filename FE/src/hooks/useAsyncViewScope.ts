import { useLayoutEffect, useState } from 'react'

import { createAsyncViewScope } from '@/hooks/asyncViewScope'

export const useAsyncViewScope = () => {
  const [scope] = useState(createAsyncViewScope)
  useLayoutEffect(() => scope.mount(), [scope])
  return scope
}
