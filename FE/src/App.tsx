import { RouterProvider } from 'react-router-dom'

import AppProviders from '@/app/providers/AppProviders'
import router from '@/routes/router'

function App() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  )
}

export default App
