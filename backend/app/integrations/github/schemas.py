from datetime import datetime

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    login: str
    id: int
    type: str
    name: str | None = None
    avatar_url: str | None = None


class GitHubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    default_branch: str
    html_url: str
    description: str | None = None
    updated_at: datetime | None = None


class GitHubPullRequestSummary(BaseModel):
    number: int
    title: str
    state: str
    user_login: str
    html_url: str
    created_at: datetime
    updated_at: datetime
    draft: bool = False
    # The list endpoint's raw response already includes these (same PR
    # object shape as the single-PR endpoint) - no extra API call needed.
    base_branch: str
    head_branch: str


class GitHubPullRequestDetail(GitHubPullRequestSummary):
    body: str | None = None
    additions: int
    deletions: int
    changed_files: int
    mergeable: bool | None = None
    merged: bool = False


class GitHubPullRequestFile(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str | None = None


class GitHubCommit(BaseModel):
    sha: str
    message: str
    author_name: str | None = None
    author_email: str | None = None
    committed_at: datetime | None = None
    html_url: str


class GitHubBranch(BaseModel):
    name: str
    sha: str
    protected: bool = False
    last_commit_author: str | None = None
    last_commit_at: datetime | None = None


class GitHubComparisonFile(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str | None = None


class GitHubComparison(BaseModel):
    base: str
    head: str
    status: str
    ahead_by: int
    behind_by: int
    total_commits: int
    additions: int = 0
    deletions: int = 0
    files: list[GitHubComparisonFile] = Field(default_factory=list)
