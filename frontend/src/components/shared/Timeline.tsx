import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface TimelineItem {
  id: string
  title: string
  description?: string
  timestamp: string
  tone?: 'neutral' | 'success' | 'warning' | 'danger'
  meta?: ReactNode
}

interface TimelineProps {
  items: TimelineItem[]
  className?: string
}

const toneDot: Record<NonNullable<TimelineItem['tone']>, string> = {
  neutral: 'bg-subtle-foreground',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
}

export function Timeline({ items, className }: TimelineProps) {
  return (
    <ol className={cn('flex flex-col', className)}>
      {items.map((item, index) => (
        <li key={item.id} className="relative flex gap-3 pb-6 last:pb-0">
          {index !== items.length - 1 && (
            <span className="absolute top-3 left-[5px] h-full w-px bg-border" />
          )}
          <span
            className={cn(
              'relative z-10 mt-1.5 size-2.5 shrink-0 rounded-full ring-4 ring-background',
              toneDot[item.tone ?? 'neutral'],
            )}
          />
          <div className="flex flex-1 flex-col gap-0.5 pb-1">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-foreground">{item.title}</p>
              <span className="shrink-0 text-xs text-subtle-foreground">{item.timestamp}</span>
            </div>
            {item.description && (
              <p className="text-sm text-muted-foreground">{item.description}</p>
            )}
            {item.meta}
          </div>
        </li>
      ))}
    </ol>
  )
}
