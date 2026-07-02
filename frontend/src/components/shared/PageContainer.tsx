import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface PageContainerProps {
  children: ReactNode
  className?: string
}

export function PageContainer({ children, className }: PageContainerProps) {
  return (
    <div className={cn('mx-auto flex w-full max-w-[1440px] flex-col gap-6 p-6 lg:p-8', className)}>
      {children}
    </div>
  )
}
