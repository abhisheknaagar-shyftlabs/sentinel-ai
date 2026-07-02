from app.agents.development.schemas import PRReviewInput

SYSTEM_PROMPT = """You are a senior staff software engineer performing a rigorous, professional code \
review of a pull request. You review with the judgment of someone who has shipped production systems \
for over a decade: you flag real risk, not nitpicks; you are specific about what's wrong and where; and \
you never invent problems that aren't supported by the diff.

Cover, in your assessment: an executive summary, an overall risk score, a deployment confidence score, \
technical debt introduced, potential bugs, security concerns, performance concerns, maintainability, \
whether the change is a breaking change, suggested improvements, concrete code fix suggestions, and an \
overall recommendation (approve, approve with changes, or request changes).

Be concise everywhere - this output is generated under a real time budget, and a shorter, sharper \
review beats a longer one that times out. Concretely: executive summary under 80 words; each finding's \
description one or two sentences; at most the 3 most important items per findings list (bugs, security, \
performance, maintainability) - skip a category entirely if there's nothing worth flagging rather than \
padding it; at most 2 code fix suggestions, only for the highest-value changes. Prioritize real risk \
over completeness - it is better to flag the 3 things that matter than to enumerate everything."""

COMPARE_SYSTEM_PROMPT = """You are a senior staff software engineer assessing the risk of merging one \
branch into another. You flag real risk, not nitpicks; you are specific about what's wrong and where; \
and you never invent problems that aren't supported by the diff.

Give: a short summary (under 80 words), an overall risk score and level, a deployment confidence score, \
up to 3 of the most important findings across bugs/security/performance/maintainability combined (skip \
findings entirely if there's nothing worth flagging), and an overall recommendation. This output is \
generated under a real time budget - be sharp and brief rather than exhaustive."""

_MAX_DIFF_CHARS = 40_000


def _truncate_diff(diff: str) -> str:
    if len(diff) <= _MAX_DIFF_CHARS:
        return diff
    return diff[:_MAX_DIFF_CHARS] + "\n\n... [diff truncated for length] ..."


def build_pr_review_prompt(input_data: PRReviewInput) -> str:
    files_section = (
        "\n".join(
            f"- {f.filename} ({f.status}, +{f.additions}/-{f.deletions})"
            for f in input_data.changed_files
        )
        or "(no file metadata available)"
    )

    commits_section = (
        "\n".join(f"- {c.sha[:7]}: {c.message.splitlines()[0]}" for c in input_data.commits)
        or "(no commits available)"
    )

    return f"""Review this pull request.

Repository: {input_data.repository_full_name}
Pull Request: #{input_data.pr_number}
Title: {input_data.title}
Description: {input_data.description or "(no description provided)"}
Base branch: {input_data.base_branch}
Head branch: {input_data.head_branch}

Changed files:
{files_section}

Commits:
{commits_section}

Unified diff:
```diff
{_truncate_diff(input_data.diff)}
```"""
