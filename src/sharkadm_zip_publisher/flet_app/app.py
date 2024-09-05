import pathlib
import time

import flet as ft
import yaml
from sharkadm import event
from sharkadm import utils

from sharkadm_zip_publisher.flet_app.constants import COLOR_DATASETS_MAIN, COLOR_DATASETS_REMOVE
from sharkadm_zip_publisher.flet_app.page_add_archive import PageAddArchive
from sharkadm_zip_publisher.flet_app.page_remove_archive import PageRemoveArchive
from sharkadm_zip_publisher.flet_app.page_config import PageConfig
from sharkadm_zip_publisher.flet_app.utils import fix_url_str
from sharkadm_zip_publisher.trigger import Trigger

USER_DIR = utils.get_root_directory() / 'zip_archive_publisher'
USER_DIR.mkdir(parents=True, exist_ok=True)
SAVES_PATH = pathlib.Path(USER_DIR, 'zip_archive_publisher_saves.yaml').resolve()


from sharkadm_zip_publisher.flet_app.saves import publisher_saves


class ZipArchivePublisherGUI:
    def __init__(self):

        self.page = None

        self._saves = {}

        self.logging_level = 'DEBUG'
        self.logging_format = '%(asctime)s [%(levelname)10s]    %(pathname)s [%(lineno)d] => %(funcName)s():    %(message)s'
        self.logging_format_stdout = '[%(levelname)10s] %(filename)s: %(funcName)s() [%(lineno)d] %(message)s'

        event.subscribe('log_workflow', self._on_log_workflow)

        self.app = ft.app(target=self.main)

    @property
    def _log_directory(self):
        path = pathlib.Path(pathlib.Path.home(), 'logs')
        path.mkdir(parents=True, exist_ok=True)
        return path

    def main(self, page: ft.Page):
        self.page = page
        self.page.title = 'Zip archive publisher'
        self.page.window_height = 1000
        self.page.window_width = 1200
        self._build()
        self._add_controls_to_save()
        # self.import_saves()
        publisher_saves.import_saves(self)

    def update_page(self):
        self.page.update()

    def _build(self):
        self._dialog_text = ft.Text()
        self._dlg = ft.AlertDialog(
            title=self._dialog_text
        )

        self.page_add_archive = PageAddArchive(self)
        self.page_remove_archive = PageRemoveArchive(self)
        self.page_config = PageConfig(self)

        t = ft.Tabs(
            selected_index=1,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Datasets",
                    icon=ft.icons.FOLDER_ZIP_OUTLINED,
                    content=self.page_add_archive,
                ),
                ft.Tab(
                    text="Config",
                    icon=ft.icons.SETTINGS_OUTLINED,
                    content=self.page_config,
                ),
                ft.Tab(
                    text="Ta bort datasets",
                    icon=ft.icons.DELETE_OUTLINE,
                    content=self.page_remove_archive,
                ),
            ],
            expand=1,
        )

        t.selected_index = 0

        self.page.controls.append(ft.Row([
            self._get_option_column(),
            self._get_url_col()
        ]))
        self.page.controls.append(ft.Divider(height=9, thickness=3, color=COLOR_DATASETS_MAIN))
        self.page.controls.append(t)
        self.update_page()

    def _get_url_col(self) -> ft.Column:
        self._trigger_url = ft.TextField(multiline=False, label='URL som triggar importen', width=600,
                                         on_blur=self._on_change_trigger_url)
        self._status_url = ft.TextField(multiline=False, label='URL som kollar status på importen',
                                        tooltip='Den här sätts automatiskt om trigger-url säts', width=600,
                                        on_blur=self._on_change_status_url)

        col = ft.Column(
            [
                self._trigger_url,
                self._status_url
            ]
        )
        return col

    def _get_option_column(self) -> ft.Column:
        dd_options = [ft.dropdown.Option(value) for value in publisher_saves.envs]
        self._env_dropdown = ft.Dropdown(
            width=100,
            options=dd_options,
            on_change=self._on_change_env
        )
        self._env_dropdown.value = 'TEST'

        btn = ft.ElevatedButton(text='Trigga import', on_click=self._trigger_import, bgcolor='green')

        return ft.Column([
            self._env_dropdown,
            btn
        ])

    def _on_change_env(self, event=None):
        value = self._env_dropdown.value
        publisher_saves.set_env(value)
        publisher_saves.import_saves(self)

    def _trigger_import(self, event=None):
        if not (self.trigger_url and self.status_url):
            self.show_dialog('Du måste fylla i fälten för URL!')
            return
        trig = Trigger(trigger_url=self.trigger_url, status_url=self.status_url)
        trig.trigger_import()
        self.show_dialog(f'Importen har triggats!')

    @property
    def trigger_url(self) -> str:
        return self._trigger_url.value

    @property
    def status_url(self) -> str:
        return self._status_url.value

    def _on_change_trigger_url(self, event=None):
        trigger_url = fix_url_str(self._trigger_url.value)
        self._trigger_url.value = trigger_url
        self._trigger_url.update()

        self._status_url.value = trigger_url + '/status'
        self._status_url.update()

    def _on_change_status_url(self, event=None):
        status_url = fix_url_str(self._status_url.value)
        self._status_url.value = status_url
        self._status_url.update()

    def show_dialog(self, text: str):
        self._dialog_text.value = text
        self._open_dlg()

    def _open_dlg(self, *args):
        self.page.dialog = self._dlg
        self._dlg.open = True
        self.update_page()

    def _on_log_workflow(self, msg: str) -> None:
        self._dialog_text.value = msg
        self._open_dlg()

    def _add_controls_to_save(self):
        # self._saves['page_add_archive._option_update_zip_archives'] = self.page_add_archive._option_update_zip_archives
        # self._saves[
        #     'page_add_archive._option_copy_zip_archives_to_sharkdata'] = self.page_add_archive._option_copy_zip_archives_to_sharkdata
        # self._saves[
        #     'page_add_archive._option_trigger_dataset_import'] = self.page_add_archive._option_trigger_dataset_import
        # self._saves[
        #     'page_add_archive._sharkdata_dataset_directory'] = self.page_add_archive._sharkdata_dataset_directory
        #
        # self._saves[
        #     'page_remove_archive._option_create_remove_file'] = self.page_remove_archive._option_create_remove_file
        # self._saves[
        #     'page_remove_archive._option_trigger_remove_file'] = self.page_remove_archive._option_trigger_remove_file
        # self._saves[
        #     'page_remove_archive._sharkdata_remove_dataset_directory'] = self.page_remove_archive._sharkdata_remove_dataset_directory
        #
        # self._saves['page_config._option_copy_config_to_sharkdata'] = self.page_config._option_copy_config_to_sharkdata
        # self._saves['page_config._option_trigger_config_import'] = self.page_config._option_trigger_config_import
        # self._saves['page_config._sharkdata_config_directory'] = self.page_config._sharkdata_config_directory

        publisher_saves.add_control('_trigger_url', self._trigger_url)
        publisher_saves.add_control('_status_url', self._status_url)

        publisher_saves.add_control('page_add_archive._option_update_zip_archives', self.page_add_archive._option_update_zip_archives)
        publisher_saves.add_control('page_add_archive._option_copy_zip_archives_to_sharkdata', self.page_add_archive._option_copy_zip_archives_to_sharkdata)
        publisher_saves.add_control('page_add_archive._option_trigger_dataset_import', self.page_add_archive._option_trigger_dataset_import)
        publisher_saves.add_control('page_add_archive._sharkdata_dataset_directory', self.page_add_archive._sharkdata_dataset_directory)

        publisher_saves.add_control('page_remove_archive._option_create_remove_file', self.page_remove_archive._option_create_remove_file)
        publisher_saves.add_control('page_remove_archive._option_trigger_remove_file', self.page_remove_archive._option_trigger_remove_file)
        publisher_saves.add_control('page_remove_archive._sharkdata_remove_dataset_directory', self.page_remove_archive._sharkdata_remove_dataset_directory)

        publisher_saves.add_control('page_config._option_copy_config_to_sharkdata', self.page_config._option_copy_config_to_sharkdata)
        publisher_saves.add_control('page_config._option_trigger_config_import', self.page_config._option_trigger_config_import)
        publisher_saves.add_control('page_config._sharkdata_config_directory', self.page_config._sharkdata_config_directory)

# def export_saves(self):
    #     data = {}
    #     for key, cont in self._saves.items():
    #         data[key] = cont.value
    #     with open(SAVES_PATH, 'w') as fid:
    #         yaml.safe_dump(data, fid)
    #
    # def import_saves(self):
    #     if not SAVES_PATH.exists():
    #         print('NO')
    #         return
    #     with open(SAVES_PATH) as fid:
    #         data = yaml.safe_load(fid)
    #     for key, value in data.items():
    #         parts = key.split('.')
    #         if not hasattr(self, parts[0]):
    #             continue
    #         attr = getattr(self, parts[0])
    #         for part in parts[1:]:
    #             if not hasattr(attr, part):
    #                 continue
    #             attr = getattr(attr, part)
    #         attr.value = value
    #         attr.update()



