import os
import pathlib
import shutil
import time

import flet as ft
from sharkadm import event
from sharkadm import utils as sharkadm_utils

from sharkadm_zip_publisher.archive_remover import ArchiveRemover
from sharkadm_zip_publisher.exceptions import ImportNotAvailable
from sharkadm_zip_publisher.flet_app import utils
from sharkadm_zip_publisher.flet_app.constants import COLOR_DATASETS_MAIN
from sharkadm_zip_publisher.flet_app.page_add_archive import PageAddArchive
from sharkadm_zip_publisher.flet_app.page_config import PageConfig
from sharkadm_zip_publisher.flet_app.page_log import PageLog
from sharkadm_zip_publisher.flet_app.page_transformers import PageTransformers
from sharkadm_zip_publisher.flet_app.page_remove_archive import PageRemoveArchive
from sharkadm_zip_publisher.trigger import Trigger

USER_DIR = utils.USER_DIR
SAVES_PATH = utils.SAVES_PATH

from sharkadm_zip_publisher.flet_app.saves import publisher_saves
from sharkadm_zip_publisher.flet_app import saves


class ZipArchivePublisherGUI:
    def __init__(self):

        self.page = None

        self._saves = {}

        self.logging_level = 'DEBUG'
        self.logging_format = '%(asctime)s [%(levelname)10s]    %(pathname)s [%(lineno)d] => %(funcName)s():    %(message)s'
        self.logging_format_stdout = '[%(levelname)10s] %(filename)s: %(funcName)s() [%(lineno)d] %(message)s'

        event.subscribe('log_workflow', self._on_log_workflow)

        self.app = ft.app(target=self.main)

        self._remove_log_file()

    @property
    def log_file_path(self) -> pathlib.Path:
        return USER_DIR / 'zip_publisher_log.txt'

    @property
    def env(self) -> str:
        return self._env_dropdown.value

    @property
    def restrict_data(self) -> bool:
        return self._restrict_data.value

    def _remove_log_file(self):
        if self.log_file_path.exists():
            os.remove(self.log_file_path)

    def _add_to_log_file(self, text: str) -> None:
        with open(self.log_file_path, 'a', encoding='cp1252') as fid:
            fid.write(f'{text}\n')

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
        publisher_saves.import_saves(self)
        self._check_paths()

    def update_page(self):
        self.page.update()

    def _build(self):
        self._dialog_text = ft.Text()
        self._dlg = ft.AlertDialog(
            title=self._dialog_text
        )

        self._info_text = ft.Text(bgcolor='gray')

        self.page_add_archive = PageAddArchive(self)
        self.page_remove_archive = PageRemoveArchive(self)
        self.page_config = PageConfig(self)
        self.page_log = PageLog(self)
        self.page_transformers = PageTransformers(self)

        self._tabs = ft.Tabs(
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
                ft.Tab(
                    text="Log",
                    icon=ft.icons.EDIT_DOCUMENT,
                    content=self.page_log,
                ),
                ft.Tab(
                    text="Transformationer",
                    icon=ft.icons.TRANSFORM,
                    content=self.page_transformers,
                ),
            ],
            expand=1, expand_loose=True
        )

        self._tabs.selected_index = 0

        self.page.controls.append(ft.Row([
            self._get_option_column(),
            self._get_paths_row(),
        ]))
        self.page.controls.append(ft.Divider(height=9, thickness=3, color=COLOR_DATASETS_MAIN))
        self.page.controls.append(self._tabs)
        self.page.controls.append(self._info_text)
        self.update_page()

    def _get_paths_row(self) -> ft.Row:

        label_col = ft.Column([
            ft.Text('URL som triggar importen:'),
            ft.Text('URL som kollar status på importen:'),
            ft.Text('Mapp för dataset:'),
            ft.Text('Mapp för zip-paket:'),
            ft.Text('Mapp för configfiler:'),
        ])

        btn_col = ft.Column([
            ft.Text(),
            ft.Text(),
            ft.ElevatedButton(text='Öppna mapp', on_click=self._open_datasets_directory),
            ft.ElevatedButton(text='Öppna mapp', on_click=self._open_zip_directory),
            ft.ElevatedButton(text='Öppna mapp', on_click=self._open_config_directory)
        ])

        self._trigger_url = ft.Text()
        self._status_url = ft.Text()

        self._datasets_directory = ft.Text()
        self._zip_directory = ft.Text()
        self._config_directory = ft.Text()

        self._static_variable_paths_column = ft.Column([
            self._datasets_directory,
            self._zip_directory,
            self._config_directory
        ])

        self._dynamic_variable_paths_column = ft.Column([
            self._get_dataset_directory_row(),
            self._get_zip_directory_row(),
            self._get_config_directory_row(),
        ], visible=False)

        var_col = ft.Column([
            self._static_variable_paths_column,
            self._dynamic_variable_paths_column
        ])

        val_col = ft.Column([
            self._trigger_url,
            self._status_url,
            var_col
        ])

        return ft.Row([
            label_col,
            val_col,
            btn_col
        ])

    def _get_dataset_directory_row(self) -> ft.Row:

        self._datasets_directory_dynamic = ft.Text()

        pick_datasets_directory_dialog = ft.FilePicker(on_result=self.on_select_dataset_directory)

        self.page.overlay.append(pick_datasets_directory_dialog)
        self._pick_datasets_directory_button = ft.ElevatedButton(
            "Välj mapp för dataset",
            icon=ft.icons.UPLOAD_FILE,
            on_click=lambda _: pick_datasets_directory_dialog.get_directory_path(
                dialog_title='Välj mapp för dataset',
                initial_directory=self._datasets_directory_dynamic.value
            ))

        row = ft.Row(
            [
                self._datasets_directory_dynamic,
                self._pick_datasets_directory_button,
            ]
        )
        return row

    def _get_zip_directory_row(self) -> ft.Row:

        self._zip_directory_dynamic = ft.Text()

        pick_zip_directory_dialog = ft.FilePicker(on_result=self.on_select_zip_directory)

        self.page.overlay.append(pick_zip_directory_dialog)
        self._pick_zip_directory_button = ft.ElevatedButton(
            'Välj mapp för "lokala" zip-paket',
            icon=ft.icons.UPLOAD_FILE,
            on_click=lambda _: pick_zip_directory_dialog.get_directory_path(
                dialog_title='Välj mapp för "lokala" zip-paket',
                initial_directory=self._zip_directory_dynamic.value
            ))

        row = ft.Row(
            [
                self._zip_directory_dynamic,
                self._pick_zip_directory_button,
            ]
        )
        return row

    def on_select_dataset_directory(self, e: ft.FilePickerResultEvent) -> None:
        if not e.path:
            return
        self._datasets_directory_dynamic.value = e.path
        self._datasets_directory_dynamic.update()

    def on_select_zip_directory(self, e: ft.FilePickerResultEvent) -> None:
        if not e.path:
            return
        self._zip_directory_dynamic.value = e.path
        self._zip_directory_dynamic.update()

    def _get_config_directory_row(self) -> ft.Row:

        self._config_directory_dynamic = ft.Text()

        pick_config_directory_dialog = ft.FilePicker(on_result=self.on_select_config_directory)

        self.page.overlay.append(pick_config_directory_dialog)
        self._pick_config_directory_button = ft.ElevatedButton(
                        "Välj mapp för configfiler",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: pick_config_directory_dialog.get_directory_path(
                            dialog_title='Välj mapp för configfiler',
                            initial_directory=self._config_directory_dynamic.value
                        ))

        row = ft.Row(
                [
                    self._config_directory_dynamic,
                    self._pick_config_directory_button,
                ]
            )
        return row

    def on_select_config_directory(self, e: ft.FilePickerResultEvent) -> None:
        if not e.path:
            return
        self._config_directory_dynamic.value = e.path
        self._config_directory_dynamic.update()

    def _open_datasets_directory(self, event=None):
        if not self.datasets_directory:
            return
        sharkadm_utils.open_directory(self.datasets_directory)

    def _open_zip_directory(self, event=None):
        if not self.zip_directory:
            return
        sharkadm_utils.open_directory(self.zip_directory)

    def _open_config_directory(self, event=None):
        if not self.config_directory:
            return
        sharkadm_utils.open_directory(self.config_directory)

    def _get_option_column(self) -> ft.Column:
        dd_options = [ft.dropdown.Option(value) for value in publisher_saves.selectable_envs]
        self._env_dropdown = ft.Dropdown(
            width=100,
            options=dd_options,
            on_change=self._on_change_env
        )

        self._env_dropdown.value = 'TEST'

        self._restrict_data = ft.Checkbox(label='Begränsa djupdata', value=True)

        self._trigger_btn = ft.ElevatedButton(text='Trigga import', on_click=self.trigger_import, bgcolor='green')

        return ft.Column([
            self._get_import_config_button(),
            self._env_dropdown,
            self._restrict_data,
            self._trigger_btn
        ])

    def _get_import_config_button(self) -> ft.Row:
        pick_config_files_dialog = ft.FilePicker(on_result=self._on_pick_config_files)

        self.page.overlay.append(pick_config_files_dialog)
        self._pick_config_files_button = ft.TextButton(
                        "Importera configfil(er)",
                        # icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: pick_config_files_dialog.pick_files(
                            allow_multiple=True,
                            allowed_extensions=['yaml']
                        ))

        row = ft.Row(
                [
                    self._pick_config_files_button,
                ]
            )
        return row

    def _on_pick_config_files(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        valid_paths = []
        invalid_paths = []
        pub_saves = saves.PublisherSaves()
        valid_mapping = dict((path.stem.lower(), path) for path in pub_saves.valid_save_paths)
        for file in e.files:
            source_path = pathlib.Path(file.path)
            if not valid_mapping.get(source_path.stem.lower()):
                invalid_paths.append(source_path)
                continue
            valid_paths.append(source_path)
            shutil.copy2(source_path, valid_mapping[source_path.stem.lower()])

        self._on_change_env()
        valid_str = '\n'.join([str(p) for p in valid_paths])
        invalid_str = '\n'.join([str(p) for p in invalid_paths])
        if not valid_paths:
            msg = f'Inga valda filer är godkända configfiler: \n{invalid_str}'
        elif invalid_paths:
            msg = f'Godkända configfiler som kopierats:\n{valid_str}\n\nIcke godkända configfiler:\n{invalid_str}'
        else:
            msg = f'Följande configfiler har kopierats:\n{valid_str}'
        self.show_dialog(msg)

    def _on_change_env(self, event=None):
        value = self._env_dropdown.value
        if value == 'LOKALT':
            self._static_variable_paths_column.visible = False
            self._dynamic_variable_paths_column.visible = True
            self._trigger_btn.disabled = True
        else:
            self._static_variable_paths_column.visible = True
            self._dynamic_variable_paths_column.visible = False
            self._trigger_btn.disabled = False

        # Valid restrict options
        if value not in ['TEST', 'LOKALT']:
            self._restrict_data.value = True
            self._restrict_data.disabled = True
        else:
            self._restrict_data.value = True
            self._restrict_data.disabled = False
        self._restrict_data.update()

        self._static_variable_paths_column.update()
        self._dynamic_variable_paths_column.update()
        self._trigger_btn.update()

        publisher_saves.set_env(value)
        publisher_saves.import_saves(self)
        self._check_paths()

    def change_env(self, env: str):
        if env not in publisher_saves.envs:
            return
        self._env_dropdown.value = env
        self._env_dropdown.update()
        self._on_change_env()
        print(f'{self._env_dropdown.value=}')

    def trigger_import(self, *args, on_remove=False):
        if not (self.trigger_url and self.status_url):
            self.show_dialog('Du måste fylla i fälten för URL!')
            return
        rem = ArchiveRemover(sharkdata_datasets_directory=self.datasets_directory)
        packs = rem.get_packages_waiting_to_be_removed()
        if not packs and on_remove:
            self.show_dialog('Det finns ingen info om vad som ska tas bort!')
            return
        if packs:
            msg = f'Det finns en remove.txt fil i datasetmappen med {len(packs)} rader. Vill du fortfarande trigga APIet?'
            if on_remove:
                msg = f'Är du säker på att du vill ta bort {len(packs)} paket?'
            self._trigger_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text('WARNING: remove.txt'),
                content=ft.Text(msg),
                actions=[
                    ft.TextButton('Ja', on_click=self._trigger_import),
                    ft.TextButton('Nej', on_click=lambda x: self.page.close(self._trigger_dlg)),
                    ft.TextButton('Öppna filen', on_click=lambda x: sharkadm_utils.open_file_with_default_program(rem.remove_file_path)),
                ]
            )
            self.page.open(self._trigger_dlg)
        else:
            self._trigger_import()

    def _trigger_import(self, event=None):
        t0 = time.time()
        max_time = 10
        if hasattr(self, '_trigger_dlg'):
            self.page.close(self._trigger_dlg)
        self.show_info(f'Triggar import...')
        trig = Trigger(trigger_url=self.trigger_url, status_url=self.status_url)
        # time.sleep(0.2)
        rem = ArchiveRemover(sharkdata_datasets_directory=self.datasets_directory,
                             zip_directory=self.zip_directory, )
        packs = rem.get_packages_waiting_to_be_removed()
        self._disable_on_trigger_import()
        while True:
            try:
                trig.trigger_import()
                while rem.remove_file_path.exists():
                    time.sleep(0.2)
                break
            except ImportNotAvailable:
                self.show_info('Triggern är inte tillgänglig. Försöker igen...')
                time.sleep(0.2)
                if (time.time() - t0) > max_time:
                    self.show_info(f'Triggern är inte tillgänglig. Försökte i {max_time} sekunder men nu ger jag upp!')
                    self._enable_on_trigger_import()
                    return
        if packs:
            self.show_info(f'Tar bort gamla paket under: {self.zip_directory}!')
            rem.remove_old_packs_in_zip_directory(packs)
        self._enable_on_trigger_import()
        self.show_info(f'Importen/borttagningen är klar!')

    def _disable_on_trigger_import(self):
        self._tabs.disabled = True
        self._tabs.update()
        self._trigger_btn.disabled = True
        self._trigger_btn.update()
        if hasattr(self, '_trigger_dlg'):
            self._trigger_dlg.disabled = True
            self._trigger_dlg.update()

    def _enable_on_trigger_import(self):
        self._tabs.disabled = False
        self._tabs.update()
        self._trigger_btn.disabled = False
        self._trigger_btn.update()
        if hasattr(self, '_trigger_dlg'):
            self._trigger_dlg.disabled = False
            self._trigger_dlg.update()

    @property
    def trigger_url(self) -> str:
        return self._trigger_url.value.strip()

    @property
    def status_url(self) -> str:
        return self._status_url.value.strip()

    @property
    def datasets_directory(self) -> str:
        if self._static_variable_paths_column.visible:
            return self._datasets_directory.value.strip()
        return self._datasets_directory_dynamic.value.strip()

    @property
    def config_directory(self) -> str:
        if self._static_variable_paths_column.visible:
            return self._config_directory.value.strip()
        return self._config_directory_dynamic.value.strip()

    @property
    def zip_directory(self) -> str:
        if self._static_variable_paths_column.visible:
            return self._zip_directory.value.strip()
        return self._zip_directory_dynamic.value.strip()

    def show_dialog(self, text: str):
        self.page_log.add_text(text)
        self._dialog_text.value = text
        self._open_dlg()

    def _open_dlg(self, *args):
        self.page.dialog = self._dlg
        self._dlg.open = True
        self.update_page()

    def _on_log_workflow(self, data: dict) -> None:
        self.log_workflow(data)

    def log_workflow(self, data: dict) -> None:
        level = data.get('level', '').lower()
        if level == 'debug':
            return
        if level in ['warning', 'error']:
            level = level.upper()
        text = f'{level}: {data.get("msg")}'
        self._add_to_log_file(text)
        self.show_info(text)

    def show_info(self, msg: str = '') -> None:
        self.page_log.add_text(msg)
        self._info_text.value = msg
        self._info_text.update()

    def _add_controls_to_save(self):

        publisher_saves.add_control('_trigger_url', self._trigger_url)
        publisher_saves.add_control('_status_url', self._status_url)

        publisher_saves.add_control('_datasets_directory', self._datasets_directory)
        publisher_saves.add_control('_zip_directory', self._zip_directory)
        publisher_saves.add_control('_config_directory', self._config_directory)

        publisher_saves.add_control('_datasets_directory_dynamic', self._datasets_directory_dynamic)
        publisher_saves.add_control('_zip_directory_dynamic', self._zip_directory_dynamic)
        publisher_saves.add_control('_config_directory_dynamic', self._config_directory_dynamic)

        publisher_saves.add_control('page_add_archive._option_update_zip_archives', self.page_add_archive._option_update_zip_archives)
        publisher_saves.add_control('page_add_archive._option_copy_zip_archives_to_sharkdata', self.page_add_archive._option_copy_zip_archives_to_sharkdata)
        publisher_saves.add_control('page_add_archive._option_trigger_dataset_import', self.page_add_archive._option_trigger_dataset_import)

        publisher_saves.add_control('page_remove_archive._option_create_remove_file', self.page_remove_archive._option_create_remove_file)
        publisher_saves.add_control('page_remove_archive._option_trigger_remove_file', self.page_remove_archive._option_trigger_remove_file)

        publisher_saves.add_control('page_config._option_copy_config_to_sharkdata', self.page_config._option_copy_config_to_sharkdata)
        publisher_saves.add_control('page_config._option_trigger_config_import', self.page_config._option_trigger_config_import)

    def _check_paths(self):
        for cont in [self._datasets_directory_dynamic, self._config_directory_dynamic]:
            value = cont.value.strip()
            if not value:
                continue
            if not pathlib.Path(value).exists():
                cont.value = ''
                cont.update()
