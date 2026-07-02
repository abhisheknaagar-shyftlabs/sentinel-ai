import { cn } from '@/utils/cn'
import type { RiskLevel } from '@/types/common'

interface RiskBadgeProps {
  level: RiskLevel
  className?: string
}

const riskStyles: Record<RiskLevel, string> = {
  low: 'bg-success-muted text-success',
  medium: 'bg-warning-muted text-warning',
  high: 'bg-danger-muted text-danger',
  critical: 'border border-danger/50 bg-danger text-background',
}

const riskLabel: Record<RiskLevel, string> = {
  low: 'Low risk',
  medium: 'Medium risk',
  high: 'High risk',
  critical: 'Critical risk',
}

export function RiskBadge({ level, className }: RiskBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium',
        riskStyles[level],
        className,
      )}
    >
      {riskLabel[level]}
    </span>
  )
}
