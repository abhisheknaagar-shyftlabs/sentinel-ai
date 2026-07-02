import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

type MetricTone = 'neutral' | 'success' | 'warning' | 'danger'

interface MetricCardProps {
  label: string
  value: string
  unit?: string
  tone?: MetricTone
  sparkline?: ReactNode
  className?: string
}

const toneDot: Record<MetricTone, string> = {
  neutral: 'bg-subtle-foreground',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
}

export function MetricCard({
  label,
  value,
  unit,
  tone = 'neutral',
  sparkline,
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-2 rounded-lg border border-border bg-surface p-4',
        className,
      )}
    >
      <div className="flex items-center gap-1.5">
        <span className={cn('size-1.5 shrink-0 rounded-full', toneDot[tone])} />
        <span className="truncate text-xs font-medium text-muted-foreground">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="font-mono-tabular text-xl font-semibold text-foreground">{value}</span>
        {unit && <span className="text-xs text-subtle-foreground">{unit}</span>}
      </div>
      {sparkline && <div className="h-8">{sparkline}</div>}
    </div>
  )
}
