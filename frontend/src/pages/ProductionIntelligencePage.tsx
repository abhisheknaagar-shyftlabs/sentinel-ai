import { Server, ShieldAlert, Timer, Zap } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ErrorState, LoadingState, PageContainer, PageHeader, StatCard } from '@/components/shared'
import { useProdIntelligenceSummary } from '@/features/production-intelligence/hooks/use-prod-intelligence-summary'
import { ContainersGrid } from '@/features/production-intelligence/components/ContainersGrid'
import { LogsPanel } from '@/features/production-intelligence/components/LogsPanel'
import { IncidentsPanel } from '@/features/production-intelligence/components/IncidentsPanel'

export default function ProductionIntelligencePage() {
  const { data, isLoading, isError, refetch } = useProdIntelligenceSummary()

  return (
    <PageContainer>
      <PageHeader
        title="Production Intelligence"
        description="Docker monitoring, container health, and auto recovery."
      />

      {isLoading && <LoadingState variant="cards" rows={4} />}
      {isError && <ErrorState onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Containers healthy"
              value={`${data.stats.containersHealthy}/${data.stats.containersTotal}`}
              icon={Server}
            />
            <StatCard
              label="Open incidents"
              value={String(data.stats.openIncidents)}
              icon={ShieldAlert}
              trend={data.stats.openIncidentsTrend}
            />
            <StatCard
              label="Auto-recoveries today"
              value={String(data.stats.autoRecoveriesToday)}
              icon={Zap}
            />
            <StatCard
              label="Avg. recovery time"
              value={`${data.stats.avgRecoveryTimeMinutes}m`}
              icon={Timer}
              trend={data.stats.avgRecoveryTrend}
            />
          </div>

          <Tabs defaultValue="containers">
            <TabsList>
              <TabsTrigger value="containers">Containers</TabsTrigger>
              <TabsTrigger value="logs">Logs</TabsTrigger>
              <TabsTrigger value="incidents">Incidents</TabsTrigger>
            </TabsList>
            <TabsContent value="containers">
              <ContainersGrid containers={data.containers} />
            </TabsContent>
            <TabsContent value="logs">
              <LogsPanel logs={data.logs} />
            </TabsContent>
            <TabsContent value="incidents">
              <IncidentsPanel incidents={data.incidents} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </PageContainer>
  )
}
