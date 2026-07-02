import { cn } from '@/utils/cn'
import type { HealthStatus } from '@/types/common'

interface HealthBadgeProps {
  status: HealthStatus
  className?: string
}

const healthStyles: Record<HealthStatus, string> = {
  healthy: 'bg-success-muted text-success',
  degraded: 'bg-warning-muted text-warning',
  unhealthy: 'bg-danger-muted text-danger',
  unknown: 'bg-surface-elevated text-subtle-foreground',
}

const healthDot: Record<HealthStatus, string> = {
  healthy: 'bg-success',
  degraded: 'bg-warning',
  unhealthy: 'bg-danger',
  unknown: 'bg-subtle-foreground',
}

export function HealthBadge({ status, className }: HealthBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium capitalize',
        healthStyles[status],
        className,
      )}
    >
      <span
        className={cn(
          'size-1.5 rounded-full',
          healthDot[status],
          status === 'healthy' && 'animate-pulse',
        )}
      />
      {status}
    </span>
  )
}
