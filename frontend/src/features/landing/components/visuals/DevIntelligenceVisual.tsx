import { RiskBadge } from '@/components/shared'
import { GitPullRequest } from 'lucide-react'

const prs = [
  { title: 'Refactor payment retry logic', risk: 'high' as const, confidence: 62 },
  { title: 'Add rate limiting to /webhooks', risk: 'low' as const, confidence: 96 },
  { title: 'Migrate auth session store', risk: 'medium' as const, confidence: 81 },
]

export function DevIntelligenceVisual() {
  return (
    <div className="rounded-xl border border-border bg-surface p-2 shadow-xl shadow-black/30">
      <div className="flex flex-col gap-2 rounded-lg bg-card p-4">
        <span className="text-xs font-medium text-muted-foreground">Open pull requests</span>
        {prs.map((pr) => (
          <div
            key={pr.title}
            className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface p-3"
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <GitPullRequest className="size-4 shrink-0 text-subtle-foreground" strokeWidth={1.75} />
              <span className="truncate text-sm text-foreground">{pr.title}</span>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className="font-mono-tabular text-xs text-muted-foreground">{pr.confidence}%</span>
              <RiskBadge level={pr.risk} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
