import posthog
from app.config import settings

# Configure PostHog
posthog.project_api_key = settings.POSTHOG_API_KEY
posthog.host = settings.POSTHOG_HOST or "https://app.posthog.com"

def track_event(user_id: str, event: str, properties: dict | None = None):
    """
    Capture an event in PostHog.
    user_id: UUID or string (must match frontend identify())
    event: event name
    properties: dict of event metadata
    """
    posthog.capture(
        distinct_id=user_id,
        event=event,
        properties=properties or {}
    )

def identify_user(user_id: str, traits: dict | None = None):
    """
    Identify or update user profile in PostHog.
    """
    posthog.identify(
        distinct_id=user_id,
        properties=traits or {}
    )
