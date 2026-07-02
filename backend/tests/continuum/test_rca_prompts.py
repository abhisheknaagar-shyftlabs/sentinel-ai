from app.agents.production.prompts import build_rca_prompt
from app.agents.production.schemas import RootCauseAnalysisInput
from app.integrations.docker.schemas import (
    BlockIOStats,
    ContainerDetail,
    ContainerHealthStatus,
    ContainerLogEntry,
    ContainerLogs,
    ContainerStats,
    NetworkStats,
    PortMapping,
)
from app.utils.time import utc_now


def _build_input() -> RootCauseAnalysisInput:
    container = ContainerDetail(
        id="abc123def456",
        short_id="abc123def456",
        name="postgres",
        image="postgres:16-alpine",
        status="exited",
        health=ContainerHealthStatus.UNHEALTHY,
        running=False,
        created_at=utc_now(),
        started_at=None,
        restart_count=5,
        exposed_ports=[PortMapping(container_port=5432, protocol="tcp", host_port=5433)],
        command="postgres",
        mounted_volumes=[],
        stats=ContainerStats(
            container_id="abc123def456",
            cpu_usage_percent=95.5,
            memory_usage_bytes=1_000_000_000,
            memory_limit_bytes=1_000_000_000,
            memory_usage_percent=100.0,
            network=NetworkStats(rx_bytes=1, tx_bytes=2),
            block_io=BlockIOStats(read_bytes=1, write_bytes=2),
            collected_at=utc_now(),
        ),
    )
    logs = ContainerLogs(
        container_id="abc123def456",
        lines=[ContainerLogEntry(timestamp=None, message="FATAL: out of memory")],
    )
    return RootCauseAnalysisInput(container=container, logs=logs)


def test_build_rca_prompt_includes_key_evidence():
    prompt = build_rca_prompt(_build_input())
    assert "postgres" in prompt
    assert "95.5" in prompt
    assert "restart" in prompt.lower() and "5" in prompt
    assert "out of memory" in prompt
    assert "5433" in prompt


def test_build_rca_prompt_handles_missing_stats_and_logs():
    container = ContainerDetail(
        id="x",
        short_id="x",
        name="x",
        image="x",
        status="running",
        health=ContainerHealthStatus.NONE,
        running=True,
        created_at=None,
        started_at=None,
        restart_count=0,
        stats=None,
    )
    input_data = RootCauseAnalysisInput(container=container, logs=ContainerLogs(container_id="x"))
    prompt = build_rca_prompt(input_data)
    assert "no live stats snapshot available" in prompt
    assert "no recent logs available" in prompt
