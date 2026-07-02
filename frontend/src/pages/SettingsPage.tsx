import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ErrorState, LoadingState, PageContainer, PageHeader } from '@/components/shared'
import { useSettings } from '@/features/settings/hooks/use-settings'
import { WorkspaceForm } from '@/features/settings/components/WorkspaceForm'
import { NotificationsForm } from '@/features/settings/components/NotificationsForm'
import { AiPreferencesForm } from '@/features/settings/components/AiPreferencesForm'

export default function SettingsPage() {
  const { data, isLoading, isError, refetch } = useSettings()

  return (
    <PageContainer>
      <PageHeader
        title="Settings"
        description="Workspace settings, notifications, and AI preferences."
      />

      {isLoading && <LoadingState variant="list" rows={5} />}
      {isError && <ErrorState onRetry={() => refetch()} />}

      {data && (
        <Tabs defaultValue="workspace" className="max-w-3xl">
          <TabsList>
            <TabsTrigger value="workspace">Workspace</TabsTrigger>
            <TabsTrigger value="notifications">Notifications</TabsTrigger>
            <TabsTrigger value="ai">AI preferences</TabsTrigger>
          </TabsList>
          <TabsContent value="workspace">
            <WorkspaceForm defaultValues={data.workspace} />
          </TabsContent>
          <TabsContent value="notifications">
            <NotificationsForm defaultValues={data.notifications} />
          </TabsContent>
          <TabsContent value="ai">
            <AiPreferencesForm defaultValues={data.aiPreferences} />
          </TabsContent>
        </Tabs>
      )}
    </PageContainer>
  )
}
