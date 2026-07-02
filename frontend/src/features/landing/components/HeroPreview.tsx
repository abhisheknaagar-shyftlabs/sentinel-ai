import { motion } from 'motion/react'
import { AlertTriangle, GitPullRequest, Server, TrendingUp } from 'lucide-react'
import { HealthBadge } from '@/components/shared'

const stats = [
  { label: 'Open PRs at risk', value: '3', icon: GitPullRequest, tone: 'text-warning' },
  { label: 'Containers healthy', value: '46/48', icon: Server, tone: 'text-success' },
  { label: 'Infra spend / mo', value: '$18.2k', icon: TrendingUp, tone: 'text-foreground' },
  { label: 'Open incidents', value: '0', icon: AlertTriangle, tone: 'text-success' },
]

export function HeroPreview() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className="relative w-full max-w-4xl"
    >
      <div
        className="absolute -inset-16 -z-10 rounded-full opacity-40 blur-3xl"
        style={{
          background:
            'radial-gradient(closest-side, color-mix(in oklch, var(--primary) 35%, transparent), transparent)',
        }}
      />

      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        className="overflow-hidden rounded-xl border border-border bg-surface shadow-2xl shadow-black/40"
      >
        <div className="flex items-center gap-2 border-b border-border bg-surface-elevated px-4 py-2.5">
          <span className="size-2.5 rounded-full bg-danger/60" />
          <span className="size-2.5 rounded-full bg-warning/60" />
          <span className="size-2.5 rounded-full bg-success/60" />
          <div className="ml-3 flex-1 rounded-md bg-background px-3 py-1 text-center text-xs text-subtle-foreground">
            app.sentinel.ai/dashboard
          </div>
        </div>

        <div className="grid grid-cols-[56px_1fr]">
          <div className="flex flex-col items-center gap-3 border-r border-border bg-surface py-4">
            {[GitPullRequest, Server, TrendingUp].map((Icon, i) => (
              <div
                key={i}
                className="flex size-8 items-center justify-center rounded-md text-subtle-foreground first:bg-primary-muted first:text-primary"
              >
                <Icon className="size-4" strokeWidth={1.75} />
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-3 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Engineering overview</span>
              <HealthBadge status="healthy" />
            </div>

            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              {stats.map((stat) => (
                <div key={stat.label} className="flex flex-col gap-1.5 rounded-lg border border-border bg-card p-3">
                  <stat.icon className="size-3.5 text-subtle-foreground" strokeWidth={1.75} />
                  <span className={`font-mono-tabular text-lg font-semibold ${stat.tone}`}>{stat.value}</span>
                  <span className="text-[11px] leading-tight text-subtle-foreground">{stat.label}</span>
                </div>
              ))}
            </div>

            <div className="flex h-24 items-end gap-1.5 rounded-lg border border-border bg-card p-3">
              {[40, 65, 50, 80, 60, 90, 70, 85, 55, 95, 75, 100].map((h, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-sm bg-gradient-to-t from-primary/70 to-accent-cyan/70"
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
