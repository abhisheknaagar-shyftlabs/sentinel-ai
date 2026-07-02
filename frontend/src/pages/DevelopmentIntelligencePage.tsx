import { useState } from 'react'
import { AlertOctagon, GitPullRequest, ShieldCheck, Sparkles } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ErrorState, LoadingState, PageContainer, PageHeader, StatCard } from '@/components/shared'
import { useDevIntelligenceSummary } from '@/features/development-intelligence/hooks/use-dev-intelligence-summary'
import { PullRequestsPanel } from '@/features/development-intelligence/components/PullRequestsPanel'
import { TechnicalDebtPanel } from '@/features/development-intelligence/components/TechnicalDebtPanel'
import { AiFixesPanel } from '@/features/development-intelligence/components/AiFixesPanel'
import { BranchComparisonPanel } from '@/features/development-intelligence/components/BranchComparisonPanel'
import type { PullRequest } from '@/features/development-intelligence/types'
import { formatPercent } from '@/utils/format'

export default function DevelopmentIntelligencePage() {
  const { data, isLoading, isError, refetch } = useDevIntelligenceSummary()
  const [activeTab, setActiveTab] = useState('pull-requests')
  const [compareSelection, setCompareSelection] = useState<{ base: string; head: string } | null>(null)

  function handleCompare(pr: PullRequest) {
    setCompareSelection({ base: pr.baseBranch, head: pr.branch })
    setActiveTab('branch-comparison')
  }

  return (
    <PageContainer>
      <PageHeader
        title="Development Intelligence"
        description="GitHub PR review, risk analysis, and deployment confidence."
      />

      {isLoading && <LoadingState variant="cards" rows={4} />}
      {isError && <ErrorState onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Open pull requests"
              value={String(data.stats.openPRs)}
              icon={GitPullRequest}
              trend={data.stats.openPRsTrend}
            />
            <StatCard
              label="High-risk PRs"
              value={String(data.stats.highRiskPRs)}
              icon={AlertOctagon}
            />
            <StatCard
              label="Avg. deployment confidence"
              value={formatPercent(data.stats.avgDeploymentConfidence)}
              icon={ShieldCheck}
              trend={data.stats.avgDeploymentConfidenceTrend}
            />
            <StatCard
              label="Technical debt"
              value={`${data.stats.technicalDebtHours}h`}
              icon={Sparkles}
              trend={data.stats.technicalDebtTrend}
              helpText="Estimated remediation effort"
            />
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="pull-requests">Pull requests</TabsTrigger>
              <TabsTrigger value="branch-comparison">Branch comparison</TabsTrigger>
              <TabsTrigger value="technical-debt">Technical debt</TabsTrigger>
              <TabsTrigger value="ai-fixes">AI fixes</TabsTrigger>
            </TabsList>
            <TabsContent value="pull-requests">
              <PullRequestsPanel pullRequests={data.pullRequests} onCompare={handleCompare} />
            </TabsContent>
            <TabsContent value="branch-comparison">
              <BranchComparisonPanel
                key={compareSelection ? `${compareSelection.base}...${compareSelection.head}` : 'default'}
                initialBase={compareSelection?.base}
                initialHead={compareSelection?.head}
              />
            </TabsContent>
            <TabsContent value="technical-debt">
              <TechnicalDebtPanel items={data.technicalDebt} />
            </TabsContent>
            <TabsContent value="ai-fixes">
              <AiFixesPanel fixes={data.aiFixes} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </PageContainer>
  )
}
