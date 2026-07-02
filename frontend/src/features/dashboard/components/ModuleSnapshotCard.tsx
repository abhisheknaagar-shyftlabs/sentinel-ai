import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ModuleSnapshotCardProps {
  icon: LucideIcon
  title: string
  headline: string
  detail: string
  badge: ReactNode
  linkTo: string
}

export function ModuleSnapshotCard({
  icon: Icon,
  title,
  headline,
  detail,
  badge,
  linkTo,
}: ModuleSnapshotCardProps) {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Icon className="size-4" strokeWidth={1.75} />
          {title}
        </div>
        {badge}
      </div>
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold text-foreground">{headline}</p>
        <p className="text-sm text-muted-foreground">{detail}</p>
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="mt-auto w-fit gap-1.5 px-0 text-primary hover:bg-transparent hover:text-primary"
        onClick={() => navigate(linkTo)}
      >
        View module
        <ArrowRight className="size-3.5" />
      </Button>
    </div>
  )
}
