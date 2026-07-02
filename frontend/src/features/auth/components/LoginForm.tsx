import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useLocation, useNavigate } from 'react-router-dom'
import { Loader2, Lock, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ROUTES } from '@/routes/paths'
import { useLogin } from '../hooks/use-login'
import { loginSchema, type LoginFormValues } from '../types/login-schema'

export function LoginForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const { mutateAsync, isPending, isError } = useLogin()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  async function onSubmit(values: LoginFormValues) {
    try {
      await mutateAsync(values)
      const redirectTo = (location.state as { from?: string } | null)?.from ?? ROUTES.dashboard
      navigate(redirectTo, { replace: true })
    } catch {
      // Error surfaced below via the mutation's isError state.
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">Work email</Label>
        <div className="relative">
          <Mail className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-subtle-foreground" />
          <Input
            id="email"
            type="email"
            placeholder="you@company.com"
            autoComplete="email"
            className="pl-9"
            {...register('email')}
          />
        </div>
        {errors.email && <p className="text-xs text-danger">{errors.email.message}</p>}
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="password">Password</Label>
          <a href="#" className="text-xs text-primary hover:underline">
            Forgot password?
          </a>
        </div>
        <div className="relative">
          <Lock className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-subtle-foreground" />
          <Input
            id="password"
            type="password"
            placeholder="••••••••"
            autoComplete="current-password"
            className="pl-9"
            {...register('password')}
          />
        </div>
        {errors.password && <p className="text-xs text-danger">{errors.password.message}</p>}
      </div>

      {isError && (
        <p className="rounded-md bg-danger-muted px-3 py-2 text-center text-xs text-danger">
          Invalid email or password. Please try again.
        </p>
      )}

      <Button type="submit" className="mt-1" disabled={isPending}>
        {isPending && <Loader2 className="size-4 animate-spin" />}
        Sign in
      </Button>

      <p className="text-center text-xs text-subtle-foreground">
        Demo environment — enter any email and a 6+ character password to continue.
      </p>
    </form>
  )
}
