import { CheckCircle2 } from 'lucide-react'
import { Logo } from '@/components/brand/Logo'

const points = [
  'Risk-scored PR reviews before every merge',
  'Root cause analysis the moment something breaks',
  'One number that tells leadership how engineering is really doing',
]

export function AuthBrandPanel() {
  return (
    <div className="relative hidden h-full flex-col justify-between overflow-hidden bg-surface p-10 lg:flex">
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          background:
            'radial-gradient(600px circle at 20% 20%, color-mix(in oklch, var(--primary) 18%, transparent), transparent), radial-gradient(600px circle at 80% 80%, color-mix(in oklch, var(--accent-cyan) 14%, transparent), transparent)',
        }}
      />

      <Logo className="relative z-10" />

      <div className="relative z-10 flex max-w-md flex-col gap-6">
        <blockquote className="text-2xl font-medium tracking-tight text-foreground text-balance">
          &ldquo;Know what&rsquo;s breaking before your customers do.&rdquo;
        </blockquote>
        <ul className="flex flex-col gap-3">
          {points.map((point) => (
            <li key={point} className="flex items-start gap-2.5 text-sm text-muted-foreground">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" strokeWidth={1.75} />
              {point}
            </li>
          ))}
        </ul>
      </div>

      <p className="relative z-10 text-xs text-subtle-foreground">
        AI Engineering Control Center
      </p>
    </div>
  )
}
