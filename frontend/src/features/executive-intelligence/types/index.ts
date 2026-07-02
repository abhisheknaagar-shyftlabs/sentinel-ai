import type { DeploymentConfidence, RiskLevel, Trend } from '@/types/common'

export interface ExecStats {
  engineeringHealthScore: number
  engineeringHealthTrend: Trend
  deploymentReadiness: DeploymentConfidence
  infraCostMonthly: number
  infraCostTrend: Trend
  potentialMonthlySavings: number
  incidentsThisQuarter: number
  incidentsTrend: Trend
}

export interface CostBreakdownItem {
  service: string
  monthlyCost: number
  percentOfTotal: number
  trend: Trend
}

export interface CostOptimization {
  id: string
  title: string
  description: string
  estimatedMonthlySavings: number
  effort: RiskLevel
}

export interface IncidentAnalyticsPoint {
  label: string
  value: number
}

export interface HealthDimension {
  label: string
  score: number
}

export interface ExecIntelligenceSummary {
  stats: ExecStats
  healthTrend: { label: string; value: number }[]
  healthDimensions: HealthDimension[]
  costBreakdown: CostBreakdownItem[]
  costOptimizations: CostOptimization[]
  incidentAnalytics: IncidentAnalyticsPoint[]
}
