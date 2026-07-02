import { AlertOctagon } from 'lucide-react'
import { DataTable, EmptyState, RiskBadge, type DataTableColumn } from '@/components/shared'
import type { TechnicalDebtItem } from '../types'

interface TechnicalDebtPanelProps {
  items: TechnicalDebtItem[]
}

export function TechnicalDebtPanel({ items }: TechnicalDebtPanelProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={AlertOctagon}
        title="No technical debt detected"
        description="Sentinel continuously scans your codebase for debt as PRs merge."
      />
    )
  }

  const columns: DataTableColumn<TechnicalDebtItem>[] = [
    {
      key: 'module',
      header: 'Module',
      render: (item) => <span className="font-mono-tabular text-xs">{item.module}</span>,
    },
    {
      key: 'description',
      header: 'Description',
      render: (item) => <span className="text-foreground">{item.description}</span>,
      className: 'max-w-md',
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (item) => <RiskBadge level={item.severity} />,
    },
    {
      key: 'estimatedHours',
      header: 'Est. effort',
      render: (item) => <span className="font-mono-tabular">{item.estimatedHours}h</span>,
    },
    {
      key: 'detectedAt',
      header: 'Detected',
      render: (item) => <span className="text-xs text-subtle-foreground">{item.detectedAt}</span>,
    },
  ]

  return <DataTable columns={columns} rows={items} getRowId={(item) => item.id} />
}
