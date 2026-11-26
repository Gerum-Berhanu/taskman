"""EmailProvider -> send_via_* registry used by send_mail."""

from collections.abc import Callable

from app.core.config import EmailProvider
from app.infrastructure.email.providers.resend import send_via_resend
from app.infrastructure.email.providers.smtp import send_via_smtp


ProviderRegistry: dict[EmailProvider, Callable[..., None]] = {
    EmailProvider.RESEND: send_via_resend,
    EmailProvider.SMTP: send_via_smtp,
}
