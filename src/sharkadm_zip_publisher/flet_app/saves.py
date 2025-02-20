import pathlib

import flet as ft
import yaml
from sharkadm import utils

USER_DIR = utils.get_root_directory() / 'zip_archive_publisher'
USER_DIR.mkdir(parents=True, exist_ok=True)


class PublisherSaves:
    def __init__(self):
        self._env: str = 'test'
        self._controls = {}

    def set_env(self, env: str) -> None:
        env = env.strip().upper()
        if env not in self.envs:
            raise KeyError(env)
        self._env = env

    @property
    def envs(self) -> list[str]:
        return ['TEST', 'PROD', 'UTV', 'LOKALT']

    @property
    def selectable_envs(self) -> list[str]:
        return self.envs
        # return [env for env in self.envs if env not in ['UTV']]

    @property
    def save_path(self):
        return pathlib.Path(USER_DIR, f'zip_archive_publisher_saves_{self._env}.yaml').resolve()

    @property
    def valid_save_paths(self):
        return [pathlib.Path(USER_DIR, f'zip_archive_publisher_saves_{env}.yaml') for env in self.envs]

    def add_control(self, name: str, control: ft.Control):
        self._controls[name] = control

    def export_saves(self):
        data = {}
        for key, cont in self._controls.items():
            data[key] = cont.value
        with open(self.save_path, 'w') as fid:
            yaml.safe_dump(data, fid)

    def import_saves(self, parent: ft.Control):
        self._clear_all_fields(parent)
        if not self.save_path.exists():
            return
        with open(self.save_path) as fid:
            data = yaml.safe_load(fid)
        for key, value in data.items():
            parts = key.split('.')
            if not hasattr(parent, parts[0]):
                continue
            attr = getattr(parent, parts[0])
            for part in parts[1:]:
                if not hasattr(attr, part):
                    continue
                attr = getattr(attr, part)
            attr.value = value
            attr.update()

    def _clear_all_fields(self, parent: ft.Control) -> None:
        for key, value in self._controls.items():
            parts = key.split('.')
            if not hasattr(parent, parts[0]):
                continue
            attr = getattr(parent, parts[0])
            for part in parts[1:]:
                if not hasattr(attr, part):
                    continue
                attr = getattr(attr, part)
            attr.value = ''
            attr.update()


publisher_saves = PublisherSaves()

