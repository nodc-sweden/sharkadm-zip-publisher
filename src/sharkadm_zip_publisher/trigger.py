import requests

from sharkadm_zip_publisher.exceptions import ImportNotAvailable


class Trigger:

    def __init__(self,
                 trigger_url: str = None,
                 status_url: str = None,
                 **kwargs):
        self._status_url = status_url
        self._trigger_url = trigger_url

    @property
    def status_url(self) -> str:
        return self._status_url

    @property
    def trigger_url(self) -> str:
        return self._trigger_url

    @property
    def _import_status_is_available(self):
        if requests.get(self.status_url).content.decode() == 'AVAILABLE':
            return True
        return False

    def trigger_import(self):
        if not self._import_status_is_available:
            raise ImportNotAvailable()
        requests.post(self.trigger_url)