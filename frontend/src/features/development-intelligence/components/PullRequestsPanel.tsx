import { useMemo, useState } from 'react'
import { ExternalLink, GitPullRequest, Sparkles } from 'lucide-react'
import {
  DataTable,
  EmptyState,
  FilterBar,
  RiskBadge,
  SearchInput,
  type DataTableColumn,
} from '@/components/shared'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { PullRequest } from '../types'

interface PullRequestsPanelProps {
  pullRequests: PullRequest[]
  /** "Run review" doesn't review inline anymore - it hands off to the
   * branch comparison tab (fast, reliable) with this PR's branches
   * preselected. A 30s wait behind a tiny inline button reads as broken;
   * the same wait on a dedicated comparison view reads as expected. */
  onCompare: (pr: PullRequest) => void
}

const RISK_OPTIONS = ['all', 'low', 'medium', 'high', 'critical'] as const
const STATUS_STYLES: Record<PullRequest['status'], string> = {
  open: 'text-info',
  draft: 'text-muted-foreground',
  merged: 'text-success',
}

export function PullRequestsPanel({ pullRequests, onCompare }: PullRequestsPanelProps) {
  const [search, setSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState<(typeof RISK_OPTIONS)[number]>('all')

  const filtered = useMemo(() => {
    return pullRequests.filter((pr) => {
      const matchesSearch =
        pr.title.toLowerCase().includes(search.toLowerCase()) ||
        pr.author.toLowerCase().includes(search.toLowerCase())
      const matchesRisk = riskFilter === 'all' || pr.risk === riskFilter
      return matchesSearch && matchesRisk
    })
  }, [pullRequests, search, riskFilter])

  const columns: DataTableColumn<PullRequest>[] = [
    {
      key: 'title',
      header: 'Pull request',
      render: (pr) => (
        <div className="flex flex-col gap-0.5">
          <span className="font-medium text-foreground">
            #{pr.number} {pr.title}
          </span>
          <span className="font-mono-tabular text-xs text-subtle-foreground">{pr.branch}</span>
        </div>
      ),
      className: 'max-w-xs',
    },
    { key: 'author', header: 'Author', render: (pr) => pr.author },
    {
      key: 'risk',
      header: 'Risk',
      render: (pr) => {
        if (pr.reviewed) return <RiskBadge level={pr.risk} />
        return (
          <Button size="sm" variant="outline" onClick={() => onCompare(pr)}>
            <Sparkles className="size-3.5" />
            Run review
          </Button>
        )
      },
    },
    {
      key: 'confidence',
      header: 'Deploy confidence',
      render: (pr) =>
        pr.reviewed ? (
          <span className="font-mono-tabular">{pr.deploymentConfidence}%</span>
        ) : (
          <span className="text-xs text-subtle-foreground">Not reviewed</span>
        ),
    },
    {
      key: 'diff',
      header: 'Changes',
      render: (pr) => (
        <span className="font-mono-tabular text-xs">
          <span className="text-success">+{pr.linesAdded}</span>{' '}
          <span className="text-danger">-{pr.linesRemoved}</span>
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (pr) => (
        <a
          href={pr.htmlUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(event) => event.stopPropagation()}
          className={`inline-flex items-center gap-1 text-xs font-medium capitalize hover:underline ${STATUS_STYLES[pr.status]}`}
        >
          {pr.status}
          <ExternalLink className="size-3" />
        </a>
      ),
    },
    {
      key: 'updatedAt',
      header: 'Updated',
      render: (pr) => <span className="text-xs text-subtle-foreground">{pr.updatedAt}</span>,
    },
  ]

  return (
    <div className="flex flex-col gap-4">
      <FilterBar>
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search by title or author..."
          className="w-full sm:w-64"
        />
        <Select value={riskFilter} onValueChange={(v) => setRiskFilter(v as typeof riskFilter)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Risk level" />
          </SelectTrigger>
          <SelectContent>
            {RISK_OPTIONS.map((option) => (
              <SelectItem key={option} value={option} className="capitalize">
                {option === 'all' ? 'All risk levels' : option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterBar>

      {filtered.length === 0 ? (
        <EmptyState
          icon={GitPullRequest}
          title="No pull requests match your filters"
          description="Try adjusting your search or risk filter."
        />
      ) : (
        <DataTable columns={columns} rows={filtered} getRowId={(pr) => pr.id} />
      )}
    </div>
  )
}
