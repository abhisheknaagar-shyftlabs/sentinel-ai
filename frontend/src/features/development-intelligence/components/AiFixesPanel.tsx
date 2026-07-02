import { Sparkles } from 'lucide-react'
import { EmptyState } from '@/components/shared'
import { cn } from '@/utils/cn'
import type { AiFix } from '../types'

interface AiFixesPanelProps {
  fixes: AiFix[]
}

const statusStyles: Record<AiFix['status'], string> = {
  suggested: 'bg-info-muted text-info',
  applied: 'bg-success-muted text-success',
  dismissed: 'bg-surface-elevated text-subtle-foreground',
}

export function AiFixesPanel({ fixes }: AiFixesPanelProps) {
  if (fixes.length === 0) {
    return (
      <EmptyState
        icon={Sparkles}
        title="No AI fixes yet"
        description="When Sentinel finds an issue it can resolve automatically, it will show up here."
      />
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {fixes.map((fix) => (
        <div key={fix.id} className="flex flex-col gap-3 rounded-lg border border-border bg-card p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary-muted">
                <Sparkles className="size-3.5 text-primary" strokeWidth={1.75} />
              </span>
              <span className="font-mono-tabular text-xs text-subtle-foreground">
                PR #{fix.prNumber}
              </span>
            </div>
            <span
              className={cn(
                'rounded-md px-2 py-0.5 text-xs font-medium capitalize',
                statusStyles[fix.status],
              )}
            >
              {fix.status}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-sm font-semibold text-foreground">{fix.title}</p>
            <p className="text-sm text-muted-foreground">{fix.description}</p>
          </div>
          <div className="mt-auto flex items-center gap-2 text-xs text-subtle-foreground">
            <span className="font-mono-tabular">{fix.confidence}% confidence</span>
          </div>
        </div>
      ))}
    </div>
  )
}
