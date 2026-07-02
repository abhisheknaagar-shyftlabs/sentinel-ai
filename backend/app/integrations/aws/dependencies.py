from app.integrations.aws.client import AWSCostClient

_aws_cost_client: AWSCostClient | None = None


def get_aws_cost_client() -> AWSCostClient:
    global _aws_cost_client
    if _aws_cost_client is None:
        _aws_cost_client = AWSCostClient()
    return _aws_cost_client
