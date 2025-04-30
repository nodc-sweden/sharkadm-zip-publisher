import os
import pathlib

import requests
from sharkadm import adm_logger

from sharkadm_zip_publisher.exceptions import ImportNotAvailable
from sharkadm_zip_publisher.trigger import Trigger
from sharkadm_zip_publisher import utils


class ArchiveRemover(Trigger):

    def __init__(self,
                 sharkdata_datasets_directory=None,
                 zip_directory=None,
                 trigger_url=None,
                 import_url=None
                 ):
        self._config = dict(
            sharkdata_datasets_directory=sharkdata_datasets_directory,
            zip_directory=zip_directory,
            trigger_url=trigger_url,
            status_url=import_url
        )

        self._remove_names = []

        super().__init__(**self._config)

    def create_remove_file(self):
        if not self._remove_names:
            return
        with open(self.remove_file_path, 'w', encoding='utf8') as fid:
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

    # def trigger_import(self):
    #     if not self._import_status_is_available:
    #         raise ImportNotAvailable()
    #     requests.post(self._config['url_trigger_import'])

    def set_remove_names(self, names: list[str]):
        self._remove_names = names

    def remove_old_packs_in_zip_directory(self, names: list[str]) -> None:
        if not self._config['zip_directory']:
            adm_logger.log_workflow(f'No zip_directory given. Could not copy "locally"!')
            return
        target_root = pathlib.Path(self._config['zip_directory'])
        if not target_root.exists():
            adm_logger.log_workflow(f'Invalid zip_directory: {target_root}')
            return
        current_mapped_zips = utils.get_zip_name_path_mapping(target_root)
        zips_to_remove = []
        for name in names:
            source_name_no_date = utils.get_zip_name_without_date(name)
            current_zip = current_mapped_zips.get(source_name_no_date)
            if current_zip:
                zips_to_remove.append(current_zip)

        # Remove old zips
        for path in zips_to_remove:
            adm_logger.log_workflow(f'Removing old package: {path}')
            os.remove(path)

    def get_packages_waiting_to_be_removed(self) -> list[str] | None:
        """Returns none if no file exits"""
        if not self.remove_file_path.exists():
            return None
        packs = []
        with open(self.remove_file_path, encoding='utf8') as fid:
            for line in fid:
                striped_line = line.strip()
                if not striped_line:
                    continue
                packs.append(striped_line)
        return packs
