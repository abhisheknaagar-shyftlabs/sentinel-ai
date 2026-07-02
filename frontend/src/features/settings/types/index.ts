import { z } from 'zod'

export const workspaceSchema = z.object({
  workspaceName: z.string().min(2, 'Workspace name must be at least 2 characters'),
  timezone: z.string().min(1, 'Select a timezone'),
  defaultBranch: z.string().min(1, 'Default branch is required'),
})

export const notificationsSchema = z.object({
  incidentAlerts: z.boolean(),
  prRiskAlerts: z.boolean(),
  weeklyDigest: z.boolean(),
  costAlerts: z.boolean(),
  notificationEmail: z.string().email('Enter a valid email address'),
})

export const aiPreferencesSchema = z.object({
  autoFixEnabled: z.boolean(),
  autoRecoveryEnabled: z.boolean(),
  riskSensitivity: z.enum(['conservative', 'balanced', 'aggressive']),
  minConfidenceThreshold: z.number().min(0).max(100),
})

export type WorkspaceFormValues = z.infer<typeof workspaceSchema>
export type NotificationsFormValues = z.infer<typeof notificationsSchema>
export type AiPreferencesFormValues = z.infer<typeof aiPreferencesSchema>

export interface SettingsData {
  workspace: WorkspaceFormValues
  notifications: NotificationsFormValues
  aiPreferences: AiPreferencesFormValues
}
