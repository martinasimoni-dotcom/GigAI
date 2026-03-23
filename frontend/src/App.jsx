import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import SplashScreen from './components/SplashScreen'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 10000,
    }
  }
})

export default function App() {
  const [showSplash, setShowSplash] = useState(true)

  return (
    <QueryClientProvider client={queryClient}>
      {showSplash
        ? <SplashScreen onEnter={() => setShowSplash(false)} />
        : <Dashboard />
      }
    </QueryClientProvider>
  )
}
