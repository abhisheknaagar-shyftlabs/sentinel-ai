import { Link } from 'react-router-dom'
import { Logo } from '@/components/brand/Logo'
import { ThemeToggle } from '@/components/shared'
import { AuthBrandPanel } from '@/features/auth/components/AuthBrandPanel'
import { LoginForm } from '@/features/auth/components/LoginForm'
import { ROUTES } from '@/routes/paths'

export default function LoginPage() {
  return (
    <div className="relative grid min-h-svh lg:grid-cols-2">
      <div className="absolute top-4 right-4 z-10">
        <ThemeToggle />
      </div>

      <AuthBrandPanel />

      <div className="flex flex-col items-center justify-center gap-8 px-6 py-16">
        <Link to={ROUTES.landing} className="lg:hidden">
          <Logo />
        </Link>

        <div className="flex w-full max-w-sm flex-col gap-8">
          <div className="flex flex-col gap-1.5 text-center">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Welcome back</h1>
            <p className="text-sm text-muted-foreground">Sign in to your Sentinel AI workspace</p>
          </div>

          <LoginForm />
        </div>
      </div>
    </div>
  )
}
