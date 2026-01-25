"""Email Agent - Send query results via email."""

from .sender import EmailAgent
from .templates import EMAIL_TEMPLATE_HTML, EMAIL_TEMPLATE_PLAIN

__all__ = ["EmailAgent", "EMAIL_TEMPLATE_HTML", "EMAIL_TEMPLATE_PLAIN"]