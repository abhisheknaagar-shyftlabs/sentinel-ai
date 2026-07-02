import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/utils/cn'

interface FilterBarProps {
  children: ReactNode
  onClear?: () => void
  className?: string
}

export function FilterBar({ children, onClear, className }: FilterBarProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-lg border border-border bg-surface p-3 sm:flex-row sm:items-center sm:justify-between',
        className,
      )}
    >
      <div className="flex flex-1 flex-wrap items-center gap-2">{children}</div>
      {onClear && (
        <Button variant="ghost" size="sm" onClick={onClear} className="shrink-0">
          Clear filters
        </Button>
      )}
    </div>
  )
}
