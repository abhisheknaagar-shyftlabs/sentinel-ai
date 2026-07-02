import asyncio
from datetime import date, timedelta
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.integrations.aws.exceptions import AWSCredentialsError, AWSUnavailableError
from app.integrations.aws.schemas import CostSummary, ServiceCost


class AWSCostClient:
    """Thin async wrapper over AWS Cost Explorer. Cost Explorer is a global
    service reachable only via the us-east-1 endpoint regardless of where
    workloads actually run. Every boto3 call is blocking, so it's offloaded
    to a thread - same pattern as DockerClient.

    Accepts an injected `client` so tests never need real AWS credentials."""

    def __init__(self, profile_name: str | None = None, client: Any | None = None) -> None:
        self._profile_name = profile_name
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                session = (
                    boto3.Session(profile_name=self._profile_name)
                    if self._profile_name
                    else boto3.Session()
                )
                self._client = session.client("ce", region_name="us-east-1")
            except (BotoCoreError, NoCredentialsError) as exc:
                raise AWSCredentialsError(f"Could not create AWS Cost Explorer client: {exc}") from exc
        return self._client

    async def get_monthly_cost_by_service(self) -> CostSummary:
        return await asyncio.to_thread(self._get_monthly_cost_by_service_sync)

    def _get_monthly_cost_by_service_sync(self) -> CostSummary:
        today = date.today()
        start = today.replace(day=1)
        end = today + timedelta(days=1)  # Cost Explorer's End is exclusive

        try:
            response = self._get_client().get_cost_and_usage(
                TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
        except NoCredentialsError as exc:
            raise AWSCredentialsError("No AWS credentials available") from exc
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDeniedException", "UnrecognizedClientException"):
                raise AWSCredentialsError(f"AWS credentials lack Cost Explorer access: {exc}") from exc
            raise AWSUnavailableError(f"AWS Cost Explorer error: {exc}") from exc
        except BotoCoreError as exc:
            raise AWSUnavailableError(f"AWS Cost Explorer error: {exc}") from exc

        return _parse_cost_response(response)


def _parse_cost_response(response: dict) -> CostSummary:
    groups = (response.get("ResultsByTime") or [{}])[0].get("Groups", [])
    entries: list[tuple[str, float]] = []
    total = 0.0
    for group in groups:
        amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
        if amount <= 0:
            continue
        service_name = group["Keys"][0] if group.get("Keys") else "Unknown"
        entries.append((service_name, amount))
        total += amount

    entries.sort(key=lambda item: item[1], reverse=True)
    services = [
        ServiceCost(
            service=name,
            monthly_cost=round(amount, 2),
            percent_of_total=round((amount / total) * 100, 1) if total else 0.0,
        )
        for name, amount in entries
    ]
    return CostSummary(total_monthly_cost=round(total, 2), by_service=services)
