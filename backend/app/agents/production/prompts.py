from app.agents.production.schemas import RootCauseAnalysisInput

SYSTEM_PROMPT = """You are a senior site reliability engineer diagnosing a production container issue. \
You reason only from the evidence you're given - live container metadata, resource stats, and recent \
logs - and never invent a cause the evidence doesn't support. When the evidence is ambiguous, say so \
and reflect that honestly in your confidence score rather than guessing with false certainty.

Diagnose: why the container is in its current state, the likely root cause with supporting evidence, \
a confidence score (0-100), the business impact and severity, recommended actions, whether an automatic \
restart would be safe, whether human intervention is required, and a potential long-term fix.

This is diagnosis only - you are not being asked to restart or modify anything."""

# Deliberately smaller than SYSTEM_PROMPT's ask, matching IncidentDiagnosis's
# flatter schema - see that schema's docstring for why. Used only by the
# health monitor's automatic incident path.
INCIDENT_DIAGNOSIS_SYSTEM_PROMPT = """You are a senior site reliability engineer diagnosing a production \
container issue for an automated incident pipeline. You reason only from the evidence you're given - live \
container metadata, resource stats, and recent logs - and never invent a cause the evidence doesn't support.

Give a one-paragraph summary of the likely root cause, a severity level, a confidence score (0-100), up to \
3 of the most important recommended actions, whether an automatic restart would be safe, and whether human \
intervention is required. Be concise everywhere - this feeds a Slack alert, not a report.

This is diagnosis only - you are not being asked to restart or modify anything."""

_MAX_LOG_LINES = 200
_MAX_LOG_CHARS = 20_000


def _format_logs(input_data: RootCauseAnalysisInput) -> str:
    lines = input_data.logs.lines[-_MAX_LOG_LINES:]
    if not lines:
        return "(no recent logs available)"
    formatted = "\n".join(
        f"[{line.timestamp.isoformat() if line.timestamp else '?'}] {line.message}" for line in lines
    )
    if len(formatted) > _MAX_LOG_CHARS:
        formatted = formatted[-_MAX_LOG_CHARS:]
        formatted = "... [truncated] ...\n" + formatted
    return formatted


def _format_ports(input_data: RootCauseAnalysisInput) -> str:
    ports = input_data.container.exposed_ports
    if not ports:
        return "(none)"
    return ", ".join(
        f"{p.container_port}/{p.protocol}" + (f" -> {p.host_ip}:{p.host_port}" if p.host_port else " (unpublished)")
        for p in ports
    )


def _format_mounts(input_data: RootCauseAnalysisInput) -> str:
    mounts = input_data.container.mounted_volumes
    if not mounts:
        return "(none)"
    return ", ".join(f"{m.source} -> {m.destination} ({m.mode})" for m in mounts)


def _format_stats(input_data: RootCauseAnalysisInput) -> str:
    stats = input_data.container.stats
    if stats is None:
        return "(no live stats snapshot available)"
    return (
        f"CPU: {stats.cpu_usage_percent}%\n"
        f"Memory: {stats.memory_usage_bytes} / {stats.memory_limit_bytes} bytes "
        f"({stats.memory_usage_percent}%)\n"
        f"Network: rx={stats.network.rx_bytes} bytes, tx={stats.network.tx_bytes} bytes\n"
        f"Block IO: read={stats.block_io.read_bytes} bytes, write={stats.block_io.write_bytes} bytes"
    )


def build_rca_prompt(input_data: RootCauseAnalysisInput) -> str:
    container = input_data.container
    return f"""Diagnose this container.

Container: {container.name} ({container.short_id})
Image: {container.image}
Status: {container.status}
Health: {container.health.value}
Running: {container.running}
Created: {container.created_at.isoformat() if container.created_at else "unknown"}
Started: {container.started_at.isoformat() if container.started_at else "never started"}
Restart count: {container.restart_count}
Command: {container.command or "(default)"}

Exposed ports: {_format_ports(input_data)}
Mounted volumes: {_format_mounts(input_data)}

Live resource stats:
{_format_stats(input_data)}

Recent logs (oldest to newest):
{_format_logs(input_data)}
"""
