import { TrendingDown } from 'lucide-react'
import { EmptyState } from '@/components/shared'
import { Badge } from '@/components/ui/badge'
import { formatCurrency } from '@/utils/format'
import { cn } from '@/utils/cn'
import type { RiskLevel } from '@/types/common'
import type { CostOptimization } from '../types'

interface CostOptimizationsPanelProps {
  optimizations: CostOptimization[]
}

const effortLabel: Record<RiskLevel, string> = {
  low: 'Low effort',
  medium: 'Medium effort',
  high: 'High effort',
  critical: 'High effort',
}

const effortStyle: Record<RiskLevel, string> = {
  low: 'bg-success-muted text-success',
  medium: 'bg-warning-muted text-warning',
  high: 'bg-danger-muted text-danger',
  critical: 'bg-danger-muted text-danger',
}

export function CostOptimizationsPanel({ optimizations }: CostOptimizationsPanelProps) {
  if (optimizations.length === 0) {
    return (
      <EmptyState
        icon={TrendingDown}
        title="No optimizations found"
        description="Your infrastructure is already running efficiently."
      />
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {optimizations.map((opt) => (
        <div
          key={opt.id}
          className="flex flex-col gap-3 rounded-lg border border-border bg-card p-5 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold text-foreground">{opt.title}</p>
              <Badge className={cn('border-0', effortStyle[opt.effort])}>
                {effortLabel[opt.effort]}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{opt.description}</p>
          </div>
          <div className="flex shrink-0 flex-col items-start sm:items-end">
            <span className="font-mono-tabular text-lg font-semibold text-success">
              {formatCurrency(opt.estimatedMonthlySavings)}
            </span>
            <span className="text-xs text-subtle-foreground">est. monthly savings</span>
          </div>
        </div>
      ))}
    </div>
  )
}
