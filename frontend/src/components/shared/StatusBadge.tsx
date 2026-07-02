import { cn } from '@/utils/cn'
import type { ConnectionStatus, DeploymentConfidence, IncidentStatus } from '@/types/common'

type Status = ConnectionStatus | DeploymentConfidence | IncidentStatus

interface StatusBadgeProps {
  status: Status
  label?: string
  className?: string
}

const statusStyles: Record<Status, string> = {
  connected: 'bg-success-muted text-success',
  safe: 'bg-success-muted text-success',
  resolved: 'bg-success-muted text-success',
  monitoring: 'bg-info-muted text-info',
  investigating: 'bg-warning-muted text-warning',
  caution: 'bg-warning-muted text-warning',
  pending: 'bg-warning-muted text-warning',
  open: 'bg-danger-muted text-danger',
  blocked: 'bg-danger-muted text-danger',
  error: 'bg-danger-muted text-danger',
  disconnected: 'bg-surface-elevated text-subtle-foreground',
}

const statusDot: Record<Status, string> = {
  connected: 'bg-success',
  safe: 'bg-success',
  resolved: 'bg-success',
  monitoring: 'bg-info',
  investigating: 'bg-warning',
  caution: 'bg-warning',
  pending: 'bg-warning',
  open: 'bg-danger',
  blocked: 'bg-danger',
  error: 'bg-danger',
  disconnected: 'bg-subtle-foreground',
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium capitalize',
        statusStyles[status],
        className,
      )}
    >
      <span className={cn('size-1.5 rounded-full', statusDot[status])} />
      {label ?? status}
    </span>
  )
}
