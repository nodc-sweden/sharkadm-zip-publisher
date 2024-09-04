import pathlib
import shutil

import flet as ft
import requests

from sharkadm_zip_publisher.exceptions import ImportNotAvailable


class ConfigPublisher:

    def __init__(self,
                 sharkdata_config_directory=None,
                 trigger_url=None,
                 import_url=None
                 ):
        self._config = dict(
            sharkdata_config_directory=sharkdata_config_directory,
            url_trigger_import=trigger_url,
            url_import_status=import_url
        )

        self._config_files = []

        if not all(list(self._config.values())):
            raise Exception('Missing input parameters!')

    def copy_config_files_to_sharkdata(self):
        target_root = pathlib.Path(self._config['sharkdata_config_directory'])
        for source_path in self.config_files:
            target_path = target_root / source_path.name
            shutil.copy2(source_path, target_path)

    @property
    def config_files(self) -> list[pathlib.Path]:
        return [pathlib.Path(path) for path in self._config_files]

    @property
    def sharkdata_config_directory(self) -> str:
        return self._config['sharkdata_config_directory']

    @property
    def url_import_status(self) -> str:
        return self._config['url_import_status']

    @property
    def url_trigger_import(self) -> str:
        return self._config['url_trigger_import']

    @property
    def _import_status_is_available(self):
        if requests.get(self.url_import_status).content.decode() == 'AVAILABLE':
            return True
        return False

    def trigger_import(self):
        if not self._import_status_is_available:
            raise ImportNotAvailable()
        requests.post(self._config['url_trigger_import'])

    def set_config_paths(self, paths: list[str | pathlib.Path]):
        self._config_files = paths


class ConfigPath(ft.UserControl):
    def __init__(self, path: str, on_delete=None):
        super().__init__()
        self.path = str(path)
        self._on_delete = on_delete

    def build(self):
        return ft.Row([
            ft.IconButton(
                ft.icons.DELETE_OUTLINE,
                tooltip="Ta bort",
                on_click=self._delete,
            ),
            ft.Text(self.path),

        ])

    def _delete(self, e):
        self._on_delete(self)
