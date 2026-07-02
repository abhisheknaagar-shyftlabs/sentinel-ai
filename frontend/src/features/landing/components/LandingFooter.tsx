import { Logo } from '@/components/brand/Logo'

export function LandingFooter() {
  return (
    <footer className="border-t border-border px-6 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
        <Logo />
        <p className="text-xs text-subtle-foreground">
          © {new Date().getFullYear()} Sentinel AI. All systems observed.
        </p>
      </div>
    </footer>
  )
}
