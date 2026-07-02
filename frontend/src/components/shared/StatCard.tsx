import type { LucideIcon } from 'lucide-react'
import { ArrowDown, ArrowRight, ArrowUp } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { Trend } from '@/types/common'

interface StatCardProps {
  label: string
  value: string
  icon?: LucideIcon
  trend?: Trend
  helpText?: string
  className?: string
}

const trendIcon = {
  up: ArrowUp,
  down: ArrowDown,
  flat: ArrowRight,
}

export function StatCard({ label, value, icon: Icon, trend, helpText, className }: StatCardProps) {
  const TrendIcon = trend ? trendIcon[trend.direction] : null

  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-lg border border-border bg-card p-5 transition-colors hover:border-border-strong',
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
        {Icon && <Icon className="size-4 text-subtle-foreground" strokeWidth={1.75} />}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
        <span className="font-mono-tabular text-2xl font-semibold text-foreground xl:text-3xl">
          {value}
        </span>
        {trend && TrendIcon && (
          <span
            className={cn(
              'flex shrink-0 items-center gap-0.5 rounded-md px-1.5 py-0.5 text-xs font-medium',
              trend.isPositive
                ? 'bg-success-muted text-success'
                : trend.direction === 'flat'
                  ? 'bg-surface-elevated text-muted-foreground'
                  : 'bg-danger-muted text-danger',
            )}
          >
            <TrendIcon className="size-3" strokeWidth={2} />
            {trend.changePercent}%
          </span>
        )}
      </div>
      {helpText && <span className="text-xs text-subtle-foreground">{helpText}</span>}
    </div>
  )
}
