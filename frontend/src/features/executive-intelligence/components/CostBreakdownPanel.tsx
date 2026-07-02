import { ArrowDown, ArrowRight, ArrowUp } from 'lucide-react'
import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/format'
import type { CostBreakdownItem } from '../types'

interface CostBreakdownPanelProps {
  items: CostBreakdownItem[]
}

const trendIcon = { up: ArrowUp, down: ArrowDown, flat: ArrowRight }

export function CostBreakdownPanel({ items }: CostBreakdownPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      {items.map((item) => {
        const TrendIcon = trendIcon[item.trend.direction]
        return (
          <div key={item.service} className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="text-foreground">{item.service}</span>
              <div className="flex items-center gap-2">
                <span className="font-mono-tabular font-medium text-foreground">
                  {formatCurrency(item.monthlyCost)}
                </span>
                <span
                  className={cn(
                    'flex items-center gap-0.5 text-xs',
                    item.trend.direction === 'flat'
                      ? 'text-subtle-foreground'
                      : item.trend.isPositive
                        ? 'text-success'
                        : 'text-danger',
                  )}
                >
                  <TrendIcon className="size-3" />
                  {item.trend.changePercent}%
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-elevated">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary to-accent-cyan"
                  style={{ width: `${item.percentOfTotal}%` }}
                />
              </div>
              <span className="w-9 text-right font-mono-tabular text-xs text-subtle-foreground">
                {item.percentOfTotal}%
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
