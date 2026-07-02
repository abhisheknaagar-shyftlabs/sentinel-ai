import type { ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import { useTheme } from '@/hooks/use-theme'
import { queryClient } from './query-client'

function ThemeSync({ children }: { children: ReactNode }) {
  // Keeps the `dark` class on <html> in sync with the persisted theme,
  // app-wide, regardless of which surface (or none) renders a toggle.
  useTheme()
  return children
}

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeSync>
        <TooltipProvider delayDuration={200}>
          {children}
          <Toaster position="bottom-right" />
        </TooltipProvider>
      </ThemeSync>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}
