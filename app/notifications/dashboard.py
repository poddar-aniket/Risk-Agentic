"""
DashboardNotifier — no-op/log implementation. The dashboard's approval queue
IS the notification surface for this build, so this just logs for now.
"""
import logging

from app.notifications.base import NotificationService

logger = logging.getLogger(__name__)


class DashboardNotifier(NotificationService):
    def notify(self, decision) -> None:
        logger.info("Decision ready for review: %s", decision)
