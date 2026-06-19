"""
NotificationService — abstract interface. DashboardNotifier is the only
implementation for the 4-5 day build; a SendGridNotifier can be added later
with zero changes to agent/pipeline code.
"""
from abc import ABC, abstractmethod


class NotificationService(ABC):
    @abstractmethod
    def notify(self, decision) -> None:
        raise NotImplementedError
