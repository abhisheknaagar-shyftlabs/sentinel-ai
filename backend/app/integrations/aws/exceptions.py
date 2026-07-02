class AWSError(Exception):
    """Base exception for AWS integration errors."""


class AWSCredentialsError(AWSError):
    """Raised when no valid AWS credentials are available."""


class AWSUnavailableError(AWSError):
    """Raised when the AWS API call fails for any other reason (permissions, throttling, region, ...)."""
