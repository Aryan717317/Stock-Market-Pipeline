class PipelineError(Exception):
    """A sanitized message safe to include in task logs."""


class PermanentError(PipelineError):
    """Retrying this run cannot resolve the input, quota, or configuration."""


class TransientError(PipelineError):
    """A bounded retry may succeed."""

    def __init__(self, message: str, retry_after: float = 0):
        super().__init__(message)
        self.retry_after = retry_after
