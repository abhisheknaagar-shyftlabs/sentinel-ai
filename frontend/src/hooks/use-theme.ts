import { useEffect } from 'react'
import { useUiStore } from '@/stores/ui-store'

/**
 * Reads the persisted theme from the UI store and keeps the `dark` class on
 * <html> in sync. First paint is handled by an inline script in index.html to
 * avoid a flash of the wrong theme; this hook keeps it consistent afterwards.
 */
export function useTheme() {
  const theme = useUiStore((state) => state.theme)
  const toggleTheme = useUiStore((state) => state.toggleTheme)
  const setTheme = useUiStore((state) => state.setTheme)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  return { theme, toggleTheme, setTheme }
}
