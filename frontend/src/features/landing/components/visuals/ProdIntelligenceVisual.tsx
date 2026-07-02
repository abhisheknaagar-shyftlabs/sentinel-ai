import { HealthBadge, Timeline } from '@/components/shared'

const containers = [
  { name: 'api-gateway', status: 'healthy' as const },
  { name: 'payments-worker', status: 'healthy' as const },
  { name: 'notifications', status: 'degraded' as const },
  { name: 'auth-service', status: 'healthy' as const },
]

export function ProdIntelligenceVisual() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-2 shadow-xl shadow-black/30">
      <div className="grid grid-cols-2 gap-2 rounded-lg bg-card p-4">
        {containers.map((c) => (
          <div key={c.name} className="flex items-center justify-between rounded-lg border border-border bg-surface px-3 py-2">
            <span className="truncate text-sm text-foreground">{c.name}</span>
            <HealthBadge status={c.status} />
          </div>
        ))}
      </div>
      <div className="rounded-lg bg-card p-4">
        <Timeline
          items={[
            {
              id: '1',
              title: 'notifications container restarted automatically',
              description: 'Root cause: memory leak in queue consumer',
              timestamp: '2m ago',
              tone: 'warning',
            },
            {
              id: '2',
              title: 'Health check recovered',
              timestamp: '1m ago',
              tone: 'success',
            },
          ]}
        />
      </div>
    </div>
  )
}
