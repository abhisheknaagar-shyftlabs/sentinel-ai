import { cn } from '@/utils/cn'
import type { HealthDimension } from '../types'

interface HealthDimensionsListProps {
  dimensions: HealthDimension[]
}

function scoreTone(score: number) {
  if (score >= 85) return 'bg-success'
  if (score >= 70) return 'bg-warning'
  return 'bg-danger'
}

export function HealthDimensionsList({ dimensions }: HealthDimensionsListProps) {
  return (
    <div className="flex flex-col gap-4">
      {dimensions.map((dimension) => (
        <div key={dimension.label} className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{dimension.label}</span>
            <span className="font-mono-tabular font-medium text-foreground">{dimension.score}</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-surface-elevated">
            <div
              className={cn('h-full rounded-full transition-all', scoreTone(dimension.score))}
              style={{ width: `${dimension.score}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
