from enum import Enum

from pydantic import BaseModel, Field


class ChangedFileSummary(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    patch: str | None = None


class CommitSummary(BaseModel):
    sha: str
    message: str
    author_name: str | None = None


class PRReviewInput(BaseModel):
    repository_full_name: str
    pr_number: int
    title: str
    description: str | None = None
    base_branch: str
    head_branch: str
    diff: str
    changed_files: list[ChangedFileSummary] = Field(default_factory=list)
    commits: list[CommitSummary] = Field(default_factory=list)


class FindingSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Finding(BaseModel):
    title: str
    description: str
    severity: FindingSeverity
    file: str | None = None
    line: int | None = None


class SuggestedFix(BaseModel):
    file: str
    description: str
    suggested_patch: str | None = None
    confidence: int = Field(
        ge=0, le=100, description="Confidence this specific fix is correct and safe to apply"
    )


class ExecutiveSummary(BaseModel):
    summary: str
    key_points: list[str] = Field(default_factory=list)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAssessment(BaseModel):
    score: int = Field(ge=0, le=100, description="Overall risk score, 0 (safest) to 100 (riskiest)")
    level: RiskLevel
    rationale: str


class DeploymentConfidence(BaseModel):
    score: int = Field(ge=0, le=100, description="Confidence this change is safe to deploy, 0-100")
    rationale: str


class TechnicalDebt(BaseModel):
    summary: str
    items: list[str] = Field(default_factory=list)


class BreakingChangeAssessment(BaseModel):
    detected: bool
    details: list[str] = Field(default_factory=list)


class Recommendation(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_CHANGES = "approve_with_changes"
    REQUEST_CHANGES = "request_changes"


class PRReviewOutput(BaseModel):
    """The full structured output of a senior-engineer-level PR review."""

    executive_summary: ExecutiveSummary
    risk_assessment: RiskAssessment
    deployment_confidence: DeploymentConfidence
    technical_debt: TechnicalDebt
    potential_bugs: list[Finding] = Field(default_factory=list)
    security_concerns: list[Finding] = Field(default_factory=list)
    performance_concerns: list[Finding] = Field(default_factory=list)
    maintainability: list[Finding] = Field(default_factory=list)
    breaking_changes: BreakingChangeAssessment
    suggested_improvements: list[str] = Field(default_factory=list)
    code_fix_suggestions: list[SuggestedFix] = Field(default_factory=list)
    recommendation: Recommendation
    recommendation_rationale: str


class CompareReviewOutput(BaseModel):
    """A deliberately smaller structured output than PRReviewOutput, used
    only by branch compare - empirically confirmed (see CLAUDE.md) that the
    full 12-section/4-list schema risks exceeding the Smart Gateway's own
    per-request timeout on real diffs, regardless of model tier. Fewer
    top-level fields and one merged findings list (instead of four separate
    ones) generates fast enough to reliably finish. PRReviewOutput itself is
    untouched - this doesn't change anything the stable PR review feature
    (POST /pulls/{n}/review) or its persistence depends on."""

    summary: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    deployment_confidence: int = Field(ge=0, le=100)
    findings: list[Finding] = Field(default_factory=list)
    recommendation: Recommendation
