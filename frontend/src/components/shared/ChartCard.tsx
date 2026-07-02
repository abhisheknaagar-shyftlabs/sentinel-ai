import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface ChartCardProps {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}

export function ChartCard({ title, description, actions, children, className }: ChartCardProps) {
  return (
    <div className={cn('flex flex-col gap-4 rounded-lg border border-border bg-card p-5', className)}>
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          {description && <p className="text-xs text-muted-foreground">{description}</p>}
        </div>
        {actions}
      </div>
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  )
}
