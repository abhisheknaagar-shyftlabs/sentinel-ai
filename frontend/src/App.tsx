import { BrowserRouter } from 'react-router-dom'
import { AppProviders } from '@/app/providers'
import { AppRoutes } from '@/routes/AppRoutes'

function App() {
  return (
    <BrowserRouter>
      <AppProviders>
        <AppRoutes />
      </AppProviders>
    </BrowserRouter>
  )
}

export default App
