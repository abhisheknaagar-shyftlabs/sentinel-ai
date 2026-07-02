import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/utils/cn'

interface LoadingStateProps {
  variant?: 'cards' | 'table' | 'list'
  rows?: number
  className?: string
}

export function LoadingState({ variant = 'cards', rows = 4, className }: LoadingStateProps) {
  if (variant === 'table') {
    return (
      <div className={cn('flex flex-col gap-2', className)}>
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-11 w-full rounded-md" />
        ))}
      </div>
    )
  }

  if (variant === 'list') {
    return (
      <div className={cn('flex flex-col gap-3', className)}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="size-8 shrink-0 rounded-full" />
            <div className="flex flex-1 flex-col gap-1.5">
              <Skeleton className="h-3.5 w-2/5" />
              <Skeleton className="h-3 w-3/5" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className={cn('grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex flex-col gap-3 rounded-lg border border-border p-5">
          <Skeleton className="h-3.5 w-1/2" />
          <Skeleton className="h-7 w-2/3" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      ))}
    </div>
  )
}
