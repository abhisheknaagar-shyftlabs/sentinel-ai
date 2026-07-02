import { ShieldCheck, Sparkles } from 'lucide-react'
import { EmptyState, RiskBadge, StatusBadge } from '@/components/shared'
import type { RiskLevel } from '@/types/common'
import type { Incident } from '../types'

interface IncidentsPanelProps {
  incidents: Incident[]
}

const severityToRisk: Record<Incident['severity'], RiskLevel> = {
  sev1: 'critical',
  sev2: 'high',
  sev3: 'medium',
  sev4: 'low',
}

export function IncidentsPanel({ incidents }: IncidentsPanelProps) {
  if (incidents.length === 0) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="No incidents"
        description="Every service has been healthy — nothing to report."
      />
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {incidents.map((incident) => (
        <div key={incident.id} className="flex flex-col gap-3 rounded-lg border border-border bg-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <RiskBadge level={severityToRisk[incident.severity]} />
              <StatusBadge status={incident.status} />
              <span className="text-xs font-medium text-subtle-foreground uppercase">
                {incident.severity}
              </span>
            </div>
            <span className="text-xs text-subtle-foreground">{incident.startedAt}</span>
          </div>

          <div className="flex flex-col gap-1">
            <p className="text-sm font-semibold text-foreground">{incident.title}</p>
            <p className="font-mono-tabular text-xs text-subtle-foreground">{incident.service}</p>
          </div>

          {incident.rootCause && (
            <div className="rounded-md bg-surface p-3">
              <p className="text-xs font-medium text-muted-foreground">Root cause analysis</p>
              <p className="mt-1 text-sm text-foreground">{incident.rootCause}</p>
            </div>
          )}

          {incident.autoRecovered && (
            <div className="flex w-fit items-center gap-1.5 rounded-md bg-success-muted px-2 py-1 text-xs font-medium text-success">
              <Sparkles className="size-3.5" />
              Automatically recovered — no human intervention required
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
