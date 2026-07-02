import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from app.integrations.aws.client import AWSCostClient
from app.integrations.aws.exceptions import AWSCredentialsError, AWSUnavailableError

SAMPLE_RESPONSE = {
    "ResultsByTime": [
        {
            "Groups": [
                {"Keys": ["Amazon Elastic Compute Cloud - Compute"], "Metrics": {"UnblendedCost": {"Amount": "86.40", "Unit": "USD"}}},
                {"Keys": ["Amazon Relational Database Service"], "Metrics": {"UnblendedCost": {"Amount": "24.00", "Unit": "USD"}}},
                {"Keys": ["AWS Free Tier Thing"], "Metrics": {"UnblendedCost": {"Amount": "0.00", "Unit": "USD"}}},
            ]
        }
    ]
}


class FakeCEClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def get_cost_and_usage(self, **kwargs):
        if self.error:
            raise self.error
        return self.response


async def test_get_monthly_cost_by_service_parses_and_sorts():
    client = AWSCostClient(client=FakeCEClient(response=SAMPLE_RESPONSE))
    summary = await client.get_monthly_cost_by_service()

    assert summary.total_monthly_cost == 110.40
    assert len(summary.by_service) == 2  # zero-cost entry dropped
    assert summary.by_service[0].service == "Amazon Elastic Compute Cloud - Compute"
    assert summary.by_service[0].percent_of_total == pytest.approx(78.3, abs=0.1)


async def test_no_credentials_raises_credentials_error():
    client = AWSCostClient(client=FakeCEClient(error=NoCredentialsError()))
    with pytest.raises(AWSCredentialsError):
        await client.get_monthly_cost_by_service()


async def test_access_denied_raises_credentials_error():
    error = ClientError({"Error": {"Code": "AccessDeniedException", "Message": "nope"}}, "GetCostAndUsage")
    client = AWSCostClient(client=FakeCEClient(error=error))
    with pytest.raises(AWSCredentialsError):
        await client.get_monthly_cost_by_service()


async def test_other_client_error_raises_unavailable():
    error = ClientError({"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "GetCostAndUsage")
    client = AWSCostClient(client=FakeCEClient(error=error))
    with pytest.raises(AWSUnavailableError):
        await client.get_monthly_cost_by_service()
