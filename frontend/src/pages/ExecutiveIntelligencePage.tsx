import { Activity, DollarSign, ShieldCheck, TrendingDown } from 'lucide-react'
import {
  ChartCard,
  ErrorState,
  LoadingState,
  PageContainer,
  PageHeader,
  SectionHeader,
  StatCard,
  StatusBadge,
  TrendAreaChart,
} from '@/components/shared'
import { useExecIntelligenceSummary } from '@/features/executive-intelligence/hooks/use-exec-intelligence-summary'
import { HealthDimensionsList } from '@/features/executive-intelligence/components/HealthDimensionsList'
import { CostBreakdownPanel } from '@/features/executive-intelligence/components/CostBreakdownPanel'
import { CostOptimizationsPanel } from '@/features/executive-intelligence/components/CostOptimizationsPanel'
import { IncidentAnalyticsChart } from '@/features/executive-intelligence/components/IncidentAnalyticsChart'
import { formatCurrency } from '@/utils/format'

export default function ExecutiveIntelligencePage() {
  const { data, isLoading, isError, refetch } = useExecIntelligenceSummary()

  return (
    <PageContainer>
      <PageHeader
        title="Executive Intelligence"
        description="Engineering health, cost optimization, and incident analytics."
      />

      {isLoading && <LoadingState variant="cards" rows={4} />}
      {isError && <ErrorState onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Engineering health"
              value={`${data.stats.engineeringHealthScore}/100`}
              icon={Activity}
              trend={data.stats.engineeringHealthTrend}
            />
            <StatCard
              label="Infra cost / mo"
              value={formatCurrency(data.stats.infraCostMonthly)}
              icon={DollarSign}
              trend={data.stats.infraCostTrend}
            />
            <StatCard
              label="Potential savings / mo"
              value={formatCurrency(data.stats.potentialMonthlySavings)}
              icon={TrendingDown}
              helpText="Identified across your infrastructure"
            />
            <StatCard
              label="Incidents this quarter"
              value={String(data.stats.incidentsThisQuarter)}
              icon={ShieldCheck}
              trend={data.stats.incidentsTrend}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <ChartCard
              title="Engineering health trend"
              description="Monthly score, last 7 months"
              className="lg:col-span-2"
              actions={<StatusBadge status={data.stats.deploymentReadiness} label="Deploy ready" />}
            >
              <TrendAreaChart data={data.healthTrend} domain={[60, 100]} />
            </ChartCard>

            <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-5">
              <SectionHeader title="Health dimensions" />
              <HealthDimensionsList dimensions={data.healthDimensions} />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-5">
              <SectionHeader
                title="Infrastructure cost"
                description={`${formatCurrency(data.stats.infraCostMonthly)} / month`}
              />
              <CostBreakdownPanel items={data.costBreakdown} />
            </div>

            <ChartCard title="Incident analytics" description="Incidents per month">
              <IncidentAnalyticsChart data={data.incidentAnalytics} />
            </ChartCard>
          </div>

          <div className="flex flex-col gap-4">
            <SectionHeader
              title="Cost optimization opportunities"
              description={`Up to ${formatCurrency(data.stats.potentialMonthlySavings)}/mo in identified savings`}
            />
            <CostOptimizationsPanel optimizations={data.costOptimizations} />
          </div>
        </>
      )}
    </PageContainer>
  )
}
