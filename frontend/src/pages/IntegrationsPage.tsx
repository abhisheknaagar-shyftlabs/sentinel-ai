import { CheckCircle2 } from 'lucide-react'
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageContainer,
  PageHeader,
} from '@/components/shared'
import { useIntegrations } from '@/features/integrations/hooks/use-integrations'
import { IntegrationCard } from '@/features/integrations/components/IntegrationCard'

export default function IntegrationsPage() {
  const { data, isLoading, isError, refetch } = useIntegrations()

  const connectedCount = data?.filter((i) => i.status === 'connected').length ?? 0

  return (
    <PageContainer>
      <PageHeader
        title="Integrations"
        description="Connect the tools Sentinel watches — GitHub, Docker, Prometheus, and Grafana."
        actions={
          data && (
            <span className="flex items-center gap-1.5 rounded-md bg-success-muted px-2.5 py-1 text-xs font-medium text-success">
              <CheckCircle2 className="size-3.5" />
              {connectedCount} of {data.length} connected
            </span>
          )
        }
      />

      {isLoading && <LoadingState variant="cards" rows={4} />}
      {isError && <ErrorState onRetry={() => refetch()} />}

      {data &&
        (data.length === 0 ? (
          <EmptyState
            title="No integrations available"
            description="Check back soon — more integrations are on the way."
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {data.map((integration) => (
              <IntegrationCard key={integration.id} integration={integration} />
            ))}
          </div>
        ))}
    </PageContainer>
  )
}
