import { RotateCw } from 'lucide-react'
import { EmptyState, HealthBadge } from '@/components/shared'
import { cn } from '@/utils/cn'
import type { Container } from '../types'

interface ContainersGridProps {
  containers: Container[]
}

function usageTone(percent: number) {
  if (percent >= 85) return 'text-danger'
  if (percent >= 65) return 'text-warning'
  return 'text-muted-foreground'
}

function UsageBar({ percent }: { percent: number }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-elevated">
      <div
        className={cn(
          'h-full rounded-full',
          percent >= 85 ? 'bg-danger' : percent >= 65 ? 'bg-warning' : 'bg-primary',
        )}
        style={{ width: `${Math.min(percent, 100)}%` }}
      />
    </div>
  )
}

export function ContainersGrid({ containers }: ContainersGridProps) {
  if (containers.length === 0) {
    return (
      <EmptyState
        title="No containers found"
        description="Connect Docker in Integrations to start monitoring containers."
      />
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {containers.map((container) => (
        <div key={container.id} className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-sm font-medium text-foreground">{container.name}</span>
            <HealthBadge status={container.status} />
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-subtle-foreground">CPU</span>
              <span className={cn('font-mono-tabular', usageTone(container.cpuPercent))}>
                {container.cpuPercent}%
              </span>
            </div>
            <UsageBar percent={container.cpuPercent} />
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-subtle-foreground">Memory</span>
              <span className={cn('font-mono-tabular', usageTone(container.memoryPercent))}>
                {container.memoryPercent}%
              </span>
            </div>
            <UsageBar percent={container.memoryPercent} />
          </div>

          <div className="flex items-center justify-between border-t border-border pt-2 text-xs text-subtle-foreground">
            <span>Uptime {container.uptime}</span>
            {container.restarts > 0 && (
              <span className="flex items-center gap-1 text-warning">
                <RotateCw className="size-3" />
                {container.restarts}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
