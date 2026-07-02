import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Logo } from '@/components/brand/Logo'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/shared'
import { ROUTES } from '@/routes/paths'
import { cn } from '@/utils/cn'

export function LandingNav() {
  const navigate = useNavigate()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 8)
    }
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={cn(
        'sticky top-0 z-30 flex h-16 items-center justify-between border-b border-transparent px-6 transition-all duration-200 lg:px-10',
        scrolled && 'border-border bg-background/80 backdrop-blur-md',
      )}
    >
      <Logo />
      <nav className="hidden items-center gap-8 md:flex">
        <a href="#modules" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
          Platform
        </a>
        <a href="#outcomes" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
          Outcomes
        </a>
        <a href="#integrations" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
          Integrations
        </a>
      </nav>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <Button variant="ghost" size="sm" onClick={() => navigate(ROUTES.login)}>
          Sign in
        </Button>
        <Button size="sm" onClick={() => navigate(ROUTES.login)}>
          Get started
        </Button>
      </div>
    </header>
  )
}
