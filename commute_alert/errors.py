class CommuteAlertError(Exception):
    """Base error for commute alert."""


class ConfigError(CommuteAlertError):
    """Raised when configuration is invalid."""


class ProviderError(CommuteAlertError):
    """Raised when a route provider fails."""


class GitHubIssueError(CommuteAlertError):
    """Raised when GitHub Issue operations fail."""
