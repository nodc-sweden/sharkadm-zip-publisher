import pathlib

import requests

from sharkadm_zip_publisher.exceptions import ImportNotAvailable


class ArchiveRemover:

    def __init__(self,
                 sharkdata_datasets_directory=None,
                 trigger_url=None,
                 import_url=None
                 ):
        self._config = dict(
            sharkdata_datasets_directory=sharkdata_datasets_directory,
            url_trigger_import=trigger_url,
            url_import_status=import_url
        )

        self._remove_names = []

        if not all(list(self._config.values())):
            raise Exception('Missing input parameters!')

    def create_remove_file(self):
        if not self._remove_names:
            return
        with open(self.remove_file_path, 'w') as fid:
            fid.write('\n'.join(sorted(self._remove_names)))

    @property
    def sharkdata_datasets_directory(self) -> pathlib.Path:
        return pathlib.Path(self._config['sharkdata_datasets_directory'])

    @property
    def url_import_status(self) -> str:
        return self._config['url_import_status']

    @property
    def url_trigger_import(self) -> str:
        return self._config['url_trigger_import']

    @property
    def remove_file_path(self) -> pathlib.Path:
        return self.sharkdata_datasets_directory / 'remove.txt'

    @property
    def _import_status_is_available(self):
        if requests.get(self.url_import_status).content.decode() == 'AVAILABLE':
            return True
        return False

    def trigger_import(self):
        if not self._import_status_is_available:
            raise ImportNotAvailable()
        requests.post(self._config['url_trigger_import'])

    def set_remove_names(self, names: list[str]):
        self._remove_names = names
