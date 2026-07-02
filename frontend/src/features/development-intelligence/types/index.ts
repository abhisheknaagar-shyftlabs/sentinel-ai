import type { RiskLevel, Trend } from '@/types/common'

export type PullRequestStatus = 'open' | 'draft' | 'merged'
export type AiFixStatus = 'suggested' | 'applied' | 'dismissed'

export interface PullRequest {
  id: string
  number: number
  title: string
  author: string
  branch: string
  baseBranch: string
  risk: RiskLevel
  deploymentConfidence: number
  filesChanged: number
  linesAdded: number
  linesRemoved: number
  status: PullRequestStatus
  updatedAt: string
  htmlUrl: string
  /** False until someone explicitly runs a review (or it's the one PR auto-reviewed on load). */
  reviewed: boolean
  repositoryId: string
}

export interface TechnicalDebtItem {
  id: string
  module: string
  description: string
  severity: RiskLevel
  estimatedHours: number
  detectedAt: string
}

export interface AiFix {
  id: string
  prNumber: number
  title: string
  description: string
  status: AiFixStatus
  confidence: number
}

export interface DevIntelligenceStats {
  openPRs: number
  openPRsTrend: Trend
  highRiskPRs: number
  avgDeploymentConfidence: number
  avgDeploymentConfidenceTrend: Trend
  technicalDebtHours: number
  technicalDebtTrend: Trend
}

export interface DevIntelligenceSummary {
  stats: DevIntelligenceStats
  pullRequests: PullRequest[]
  technicalDebt: TechnicalDebtItem[]
  aiFixes: AiFix[]
}

export type FileChangeStatus = 'added' | 'modified' | 'deleted' | 'renamed'

export interface Branch {
  name: string
  lastCommit: string
  author: string
  isProtected?: boolean
}

export interface ChangedFile {
  path: string
  status: FileChangeStatus
  additions: number
  deletions: number
  risk: RiskLevel
}

export type MergeRecommendation = 'merge' | 'caution' | 'hold'

export interface BranchComparison {
  base: string
  head: string
  identical: boolean
  commitsAhead: number
  commitsBehind: number
  filesChanged: number
  additions: number
  deletions: number
  risk: RiskLevel
  deploymentConfidence: number
  /** Holistic 0–100 score for merging head into base. */
  mergeScore: number
  recommendation: MergeRecommendation
  summary: string
  /** What merging this branch gains you. */
  gains: string[]
  /** What could break or regress if you merge. */
  risks: string[]
  changedFiles: ChangedFile[]
}
