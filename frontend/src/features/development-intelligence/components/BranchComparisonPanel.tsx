import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeftRight, GitCommitHorizontal, Minus, Plus } from 'lucide-react'
import {
  DataTable,
  EmptyState,
  ErrorState,
  LoadingState,
  RiskBadge,
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
import { cn } from '@/utils/cn'
import { DEV_INTELLIGENCE_SUMMARY_KEY } from '../hooks/use-dev-intelligence-summary'
import { useBranchComparison, useBranches } from '../hooks/use-branches'
import type { ChangedFile, DevIntelligenceSummary, FileChangeStatus, MergeRecommendation } from '../types'

const statusStyles: Record<FileChangeStatus, string> = {
  added: 'bg-success-muted text-success',
  modified: 'bg-info-muted text-info',
  deleted: 'bg-danger-muted text-danger',
  renamed: 'bg-warning-muted text-warning',
}

const recommendationMeta: Record<
  MergeRecommendation,
  { label: string; color: string; badge: string }
> = {
  merge: { label: 'Safe to merge', color: 'var(--success)', badge: 'bg-success-muted text-success' },
  caution: {
    label: 'Merge with caution',
    color: 'var(--warning)',
    badge: 'bg-warning-muted text-warning',
  },
  hold: { label: 'Hold — not recommended', color: 'var(--danger)', badge: 'bg-danger-muted text-danger' },
}

/** Counts up from 0 to `target` with an ease-out, restarting whenever target changes. */
function useCountUp(target: number, duration = 800) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    const prefersReduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
      setValue(target)
      return
    }

    let raf = 0
    let start: number | null = null
    const animate = (ts: number) => {
      if (start === null) start = ts
      const t = Math.min((ts - start) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(Math.round(target * eased))
      if (t < 1) raf = requestAnimationFrame(animate)
    }
    setValue(0)
    raf = requestAnimationFrame(animate)
    // Safety net: rAF is paused in background/throttled tabs, so guarantee the
    // final value lands even if the animation never gets a frame.
    const fallback = setTimeout(() => setValue(target), duration + 100)
    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(fallback)
    }
  }, [target, duration])

  return value
}

function MergeScoreRing({
  score,
  recommendation,
}: {
  score: number
  recommendation: MergeRecommendation
}) {
  const animatedScore = useCountUp(score)
  const radius = 34
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - animatedScore / 100)
  const color = recommendationMeta[recommendation].color

  return (
    <div className="relative flex size-24 shrink-0 items-center justify-center">
      <svg className="size-24 -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="var(--surface-elevated)" strokeWidth="7" />
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono-tabular text-2xl font-semibold text-foreground">
          {animatedScore}
        </span>
        <span className="text-[10px] text-subtle-foreground">/ 100</span>
      </div>
    </div>
  )
}

function confidenceTone(value: number) {
  if (value >= 85) return 'text-success'
  if (value >= 65) return 'text-warning'
  return 'text-danger'
}

const columns: DataTableColumn<ChangedFile>[] = [
  {
    key: 'path',
    header: 'File',
    render: (file) => <span className="font-mono-tabular text-xs">{file.path}</span>,
    className: 'max-w-md',
  },
  {
    key: 'status',
    header: 'Change',
    render: (file) => (
      <span
        className={cn(
          'rounded-md px-2 py-0.5 text-xs font-medium capitalize',
          statusStyles[file.status],
        )}
      >
        {file.status}
      </span>
    ),
  },
  {
    key: 'diff',
    header: 'Lines',
    render: (file) => (
      <span className="font-mono-tabular text-xs">
        <span className="text-success">+{file.additions}</span>{' '}
        <span className="text-danger">-{file.deletions}</span>
      </span>
    ),
  },
  { key: 'risk', header: 'Risk', render: (file) => <RiskBadge level={file.risk} /> },
]

function BranchSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-1 flex-col gap-1.5">
      <span className="text-xs font-medium text-subtle-foreground">{label}</span>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-full font-mono-tabular">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((name) => (
            <SelectItem key={name} value={name} className="font-mono-tabular">
              {name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function SummaryTile({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <span className={cn('font-mono-tabular text-xl font-semibold text-foreground', tone)}>
        {value}
      </span>
    </div>
  )
}

interface BranchComparisonPanelProps {
  initialBase?: string
  initialHead?: string
}

export function BranchComparisonPanel({
  initialBase = 'main',
  initialHead = 'feat/payment-retry',
}: BranchComparisonPanelProps = {}) {
  const { data: branches, isLoading, isError, refetch } = useBranches()
  const [base, setBase] = useState(initialBase)
  const [head, setHead] = useState(initialHead)
  const queryClient = useQueryClient()

  const {
    data: comparison,
    isLoading: isComparing,
    isError: isCompareError,
    refetch: refetchCompare,
  } = useBranchComparison(base, head)

  // A comparison result is a real risk assessment for whichever PR has this
  // exact head/base branch pair - reflect it back into the PR list so the
  // user can see at a glance that this PR has already been checked, instead
  // of it still showing "Run review" after they just ran one.
  useEffect(() => {
    if (!comparison || comparison.identical) return
    queryClient.setQueryData<DevIntelligenceSummary>(DEV_INTELLIGENCE_SUMMARY_KEY, (summary) => {
      if (!summary) return summary
      let changed = false
      const pullRequests = summary.pullRequests.map((pr) => {
        if (pr.branch !== comparison.head || pr.baseBranch !== comparison.base) return pr
        changed = true
        return {
          ...pr,
          reviewed: true,
          risk: comparison.risk,
          deploymentConfidence: comparison.deploymentConfidence,
        }
      })
      return changed ? { ...summary, pullRequests } : summary
    })
  }, [comparison, queryClient])

  if (isLoading) return <LoadingState variant="list" rows={3} />
  if (isError) return <ErrorState onRetry={() => refetch()} />

  const branchNames = branches?.map((b) => b.name) ?? []

  function swap() {
    setBase(head)
    setHead(base)
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4 sm:flex-row sm:items-end">
        <BranchSelect label="Base branch (merge into)" value={base} options={branchNames} onChange={setBase} />
        <Button
          variant="outline"
          size="icon"
          onClick={swap}
          className="shrink-0 self-center sm:mb-0.5"
          aria-label="Swap branches"
        >
          <ArrowLeftRight className="size-4" />
        </Button>
        <BranchSelect label="Compare branch (changes from)" value={head} options={branchNames} onChange={setHead} />
      </div>

      {isComparing && <LoadingState variant="cards" rows={4} />}
      {isCompareError && <ErrorState onRetry={() => refetchCompare()} />}

      {comparison &&
        !isComparing &&
        (comparison.identical ? (
          <EmptyState
            icon={GitCommitHorizontal}
            title="Nothing to compare"
            description="These branches point at the same commit."
          />
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono-tabular text-sm text-muted-foreground">
                {comparison.base}
              </span>
              <ArrowLeftRight className="size-3.5 text-subtle-foreground" />
              <span className="font-mono-tabular text-sm text-foreground">{comparison.head}</span>
              <RiskBadge level={comparison.risk} className="ml-1" />
            </div>

            <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-5 sm:flex-row sm:items-center">
              <MergeScoreRing score={comparison.mergeScore} recommendation={comparison.recommendation} />
              <div className="flex flex-1 flex-col gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Merge score</span>
                  <span
                    className={cn(
                      'rounded-md px-2 py-0.5 text-xs font-semibold',
                      recommendationMeta[comparison.recommendation].badge,
                    )}
                  >
                    {recommendationMeta[comparison.recommendation].label}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{comparison.summary}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
              <SummaryTile
                label="Commits"
                value={`${comparison.commitsAhead} ahead · ${comparison.commitsBehind} behind`}
              />
              <SummaryTile label="Files changed" value={String(comparison.filesChanged)} />
              <SummaryTile
                label="Lines changed"
                value={`+${comparison.additions} / -${comparison.deletions}`}
              />
              <SummaryTile
                label="Deployment confidence"
                value={`${comparison.deploymentConfidence}%`}
                tone={confidenceTone(comparison.deploymentConfidence)}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-5">
                <div className="flex items-center gap-2">
                  <span className="flex size-6 items-center justify-center rounded-md bg-success-muted">
                    <Plus className="size-3.5 text-success" strokeWidth={2.5} />
                  </span>
                  <span className="text-sm font-semibold text-foreground">What you gain</span>
                </div>
                <ul className="flex flex-col gap-2.5">
                  {comparison.gains.map((gain) => (
                    <li key={gain} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-success" />
                      {gain}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-5">
                <div className="flex items-center gap-2">
                  <span className="flex size-6 items-center justify-center rounded-md bg-danger-muted">
                    <Minus className="size-3.5 text-danger" strokeWidth={2.5} />
                  </span>
                  <span className="text-sm font-semibold text-foreground">What you risk</span>
                </div>
                <ul className="flex flex-col gap-2.5">
                  {comparison.risks.map((risk) => (
                    <li key={risk} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-danger" />
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <span className="text-sm font-semibold text-foreground">
                Changed files ({comparison.filesChanged})
              </span>
              <DataTable columns={columns} rows={comparison.changedFiles} getRowId={(f) => f.path} />
            </div>
          </>
        ))}
    </div>
  )
}
