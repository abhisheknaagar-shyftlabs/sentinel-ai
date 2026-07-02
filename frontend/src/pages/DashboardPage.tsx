import { DollarSign, GitPullRequest, LineChart, RefreshCw, Server, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  ChartCard,
  EmptyState,
  ErrorState,
  HealthBadge,
  LoadingState,
  PageContainer,
  PageHeader,
  RiskBadge,
  SectionHeader,
  StatCard,
  Timeline,
  TrendAreaChart,
} from '@/components/shared'
import { useDashboardSummary } from '@/features/dashboard/hooks/use-dashboard-summary'
import { ModuleSnapshotCard } from '@/features/dashboard/components/ModuleSnapshotCard'
import { formatCurrency, formatPercent } from '@/utils/format'
import { ROUTES } from '@/routes/paths'

export default function DashboardPage() {
  const { data, isLoading, isError, refetch, isFetching } = useDashboardSummary()

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        description="Your engineering organization, at a glance."
        actions={
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`size-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        }
      />

      {isLoading && <LoadingState variant="cards" rows={6} />}

      {isError && <ErrorState onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
            <StatCard
              label="Open PRs at risk"
              value={String(data.stats.openPRsAtRisk)}
              icon={GitPullRequest}
              trend={data.stats.openPRsAtRiskTrend}
            />
            <StatCard
              label="Containers healthy"
              value={`${data.stats.containersHealthy}/${data.stats.containersTotal}`}
              icon={Server}
            />
            <StatCard
              label="Open incidents"
              value={String(data.stats.openIncidents)}
              icon={ShieldCheck}
              trend={data.stats.openIncidentsTrend}
            />
            <StatCard
              label="Engineering health"
              value={String(data.stats.engineeringHealthScore)}
              icon={LineChart}
              trend={data.stats.engineeringHealthTrend}
            />
            <StatCard
              label="Infra cost / mo"
              value={formatCurrency(data.stats.infraCostMonthly)}
              icon={DollarSign}
              trend={data.stats.infraCostTrend}
            />
            <StatCard
              label="Deployment confidence"
              value={formatPercent(data.stats.deploymentConfidencePercent)}
              icon={ShieldCheck}
              trend={data.stats.deploymentConfidenceTrend}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <ModuleSnapshotCard
              icon={GitPullRequest}
              title="Development Intelligence"
              headline={data.developmentSnapshot.headline}
              detail={data.developmentSnapshot.detail}
              badge={<RiskBadge level={data.developmentSnapshot.risk} />}
              linkTo={ROUTES.developmentIntelligence}
            />
            <ModuleSnapshotCard
              icon={Server}
              title="Production Intelligence"
              headline={data.productionSnapshot.headline}
              detail={data.productionSnapshot.detail}
              badge={<HealthBadge status={data.productionSnapshot.health} />}
              linkTo={ROUTES.productionIntelligence}
            />
            <ModuleSnapshotCard
              icon={LineChart}
              title="Executive Intelligence"
              headline={data.executiveSnapshot.headline}
              detail={data.executiveSnapshot.detail}
              badge={
                <span className="text-xs font-medium text-success">
                  +{data.executiveSnapshot.trend.changePercent}%
                </span>
              }
              linkTo={ROUTES.executiveIntelligence}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <ChartCard
              title="Engineering health trend"
              description="Last 7 days"
              className="lg:col-span-2"
            >
              <TrendAreaChart data={data.healthTrend} domain={[60, 100]} />
            </ChartCard>

            <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-5">
              <SectionHeader title="Recent activity" />
              {data.recentActivity.length === 0 ? (
                <EmptyState title="No recent activity" description="Nothing to report yet." />
              ) : (
                <Timeline items={data.recentActivity} />
              )}
            </div>
          </div>
        </>
      )}
    </PageContainer>
  )
}
