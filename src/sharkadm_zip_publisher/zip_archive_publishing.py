import pathlib
import shutil
import sys
import time

import flet as ft
import requests
import yaml

from sharkadm import controller
from sharkadm import exporters
from sharkadm import transformers
from sharkadm import utils
from sharkadm.data import get_zip_archive_data_holder
from sharkadm import event
from sharkadm import adm_logger


if getattr(sys, 'frozen', False):
    ROOT_DIR = pathlib.Path(sys.executable).parent
else:
    ROOT_DIR = pathlib.Path(__file__).parent

CONFIG_DIR = pathlib.Path(ROOT_DIR, 'CONFIG_FILES').resolve()

SAVES_PATH = pathlib.Path(ROOT_DIR, 'zip_archive_publishing_saves.yaml').resolve()
CONFIG_PATH = CONFIG_DIR / 'zip_archive_publishing_config.yaml'
if not CONFIG_PATH.exists():
    CONFIG_PATH = CONFIG_DIR / 'config.yaml'


class ImportNotAvailable(Exception):
    pass


class ZipArchivePublishing:

    def __init__(self):
        self._zip_archive_paths: list[pathlib.Path] = []
        self._transformers: list[transformers.Transformer] = []
        self._updated_zip_archive_paths: list[pathlib.Path] = []
        self._config = {}

        self._controller = controller.SHARKadmController()

        self._load_config()
        self._create_transformers()

    def _load_config(self):
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(CONFIG_PATH)
        with open(CONFIG_PATH) as fid:
            self._config = yaml.safe_load(fid)

    @property
    def zip_archive_paths(self):
        return self._updated_zip_archive_paths or self._zip_archive_paths

    def update_zip_archives(self):
        self._updated_zip_archive_paths = []
        encodings = ['latin-1', 'cp1252', 'utf8']
        for path in self._zip_archive_paths:
            data_holder = get_zip_archive_data_holder(path)
            self._controller.set_data_holder(data_holder)
            self._run_transformers()
            exporter = None
            for encoding in encodings:
                try:
                    exporter = exporters.SHARKdataTxtAsGiven(encoding=encoding,
                                                             export_directory=data_holder.unzipped_archive_directory,
                                                             export_file_name=data_holder.unzipped_archive_directory / 'shark_data.txt')
                    adm_logger.log_workflow(f'Encoding is {encoding} for package {path}')

                    self._controller.export(exporter)
                    rezipped_archive_path = self._zip_directory(data_holder.unzipped_archive_directory)
                    self._updated_zip_archive_paths.append(pathlib.Path(rezipped_archive_path))
                except UnicodeEncodeError:
                    pass

            if not exporter:
                adm_logger.log_workflow(f'Could not find any working encoding for package: {path}', level=adm_logger.WARNING)
                continue

    def copy_archives_to_sharkdata(self):
        target_root = pathlib.Path(self._config['sharkdata_dataset_directory'])
        for source_path in self.zip_archive_paths:
            target_path = target_root / source_path.name
            shutil.copy2(source_path, target_path)

    @property
    def sharkdata_dataset_directory(self) -> str:
        return self._config['sharkdata_dataset_directory']

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

    def _create_transformers(self):
        self._transformers = [
            transformers.AddSwedishProjectName(),
            transformers.AddSwedishSampleOrderer(),
            transformers.AddSwedishSamplingLaboratory(),
            transformers.AddSwedishAnalyticalLaboratory(),
            transformers.AddSwedishReportingInstitute(),
        ]

    def _run_transformers(self):
        for trans in self._transformers:
            self._controller.transform(trans)

    def _zip_directory(self, directory: pathlib.Path):
        output_filename = utils.get_temp_directory('rezipped_archives') / directory.name
        return shutil.make_archive(str(output_filename), 'zip', str(directory))

    def set_zip_archive_paths(self, *args):
        self._zip_archive_paths = []
        for arg in args:
            path = pathlib.Path(arg)
            if not path.exists():
                raise FileNotFoundError(path)
            self._zip_archive_paths.append(path)


class ZipPath(ft.UserControl):
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


class ZipArchivePublisherGUI:
    def __init__(self):
        self._publisher = ZipArchivePublishing()
        self.page = None
        self._zip_paths = set()

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
        self.page.window_height = 700
        self.page.window_width = 1200
        self._build()
        self._add_controls_to_save()
        self._import_saves()

    def update_page(self):
        self.page.update()

    def _build(self):
        self._dialog_text = ft.Text()
        self._dlg = ft.AlertDialog(
            title=self._dialog_text
        )

        self._zip_paths_column = ft.Column(tight=True)
        self._option_update_zip_archives = ft.Checkbox(label='Uppdatera zip-paket', tooltip='Uppdaterar zip-peketen med _sv-columner. Uppdaterade paket skriver INTE över befintliga.')
        self._option_copy_zip_archives_to_sharkdata = ft.Checkbox(label='Kopiera zip-paket till "datasets"', tooltip=f'Kopierar zip-paketen till {self._publisher.sharkdata_dataset_directory}')
        self._option_trigger_import = ft.Checkbox(label='Importera zip-paketen', tooltip=f'Triggar APIet ({self._publisher.url_trigger_import}) \nså att arkiven som ligger i dataset-mappen importeras till sharkdata')
        options_column = ft.Column([
            self._option_update_zip_archives,
            self._option_copy_zip_archives_to_sharkdata,
            self._option_trigger_import
        ])
        container_paths = ft.Container(bgcolor='#82b2ff',
                                       content=self._zip_paths_column)
        container_options = ft.Container(bgcolor='#a1c995',
                                         content=options_column)
        self._go_button = ft.ElevatedButton(text='Kör', on_click=self._run)
        col = ft.Column([
            self._get_pick_zip_files_files_button(),
            container_paths,
            container_options,
            self._go_button
        ])

        self.page.controls.append(col)
        self.update_page()

    def _open_dlg(self, *args):
        self.page.dialog = self._dlg
        self._dlg.open = True
        self.update_page()

    def _on_log_workflow(self, msg: str) -> None:
        self._dialog_text.value = msg
        self._open_dlg()

    def _run(self, *args):
        if not any([self._option_trigger_import.value, self._option_update_zip_archives.value, self._option_copy_zip_archives_to_sharkdata.value]):
            self._dialog_text.value = 'Du har inte valt något att göra!'
            self._open_dlg()
            return
        if not self._zip_paths and any([self._option_update_zip_archives.value, self._option_copy_zip_archives_to_sharkdata.value]):
            self._dialog_text.value = 'Inga zip-arkiv valda!'
            self._open_dlg()
            return
        self._disable_buttons()
        for path in self._zip_paths:
            self._publisher.set_zip_archive_paths(path)
            if self._option_update_zip_archives.value:
                self._dialog_text.value = f'Uppdaterar {path}...'
                self._open_dlg()
                self._publisher.update_zip_archives()
            if self._option_copy_zip_archives_to_sharkdata.value:
                self._dialog_text.value = f'Kopierar {path}...'
                self._open_dlg()
                self._publisher.copy_archives_to_sharkdata()
        if self._option_trigger_import.value:
            self._dialog_text.value = f'Triggar import...'
            self._open_dlg()
            self._publisher.trigger_import()
            time.sleep(1)
        self._dialog_text.value = f'Allt klart!'
        self._open_dlg()
        self._export_saves()
        self._enable_buttons()

    def _enable_buttons(self):
        for btn in [self._pick_files_button, self._go_button]:
            btn.disabled = False
            btn.update()

    def _disable_buttons(self):
        for btn in [self._pick_files_button, self._go_button]:
            btn.disabled = True
            btn.update()

    def _add_controls_to_save(self):
        self._saves['_option_update_zip_archives'] = self._option_update_zip_archives
        self._saves['_option_copy_zip_archives_to_sharkdata'] = self._option_copy_zip_archives_to_sharkdata
        self._saves['_option_trigger_import'] = self._option_trigger_import

    def _export_saves(self):
        data = {}
        for key, cont in self._saves.items():
            data[key] = cont.value
        with open(SAVES_PATH, 'w') as fid:
            yaml.safe_dump(data, fid)

    def _import_saves(self):
        if not SAVES_PATH.exists():
            return
        with open(SAVES_PATH) as fid:
            data = yaml.safe_load(fid)
        for key, value in data.items():
            attr = getattr(self, key)
            attr.value = value
            attr.update()

    def _delete_path(self, path_control: ZipPath):
        self._zip_paths_column.controls.remove(path_control)
        self._zip_paths.remove(path_control.path)
        self.update_page()

    def _get_pick_zip_files_files_button(self) -> ft.Row:
        pick_zip_files_dialog = ft.FilePicker(on_result=self._on_pick_zip_files)

        self.page.overlay.append(pick_zip_files_dialog)
        self._pick_files_button = ft.ElevatedButton(
                        "Välj ett eller flera zip-paket",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: pick_zip_files_dialog.pick_files(
                            allow_multiple=True,
                            allowed_extensions=['zip']
                        ))

        row = ft.Row(
                [
                    self._pick_files_button,
                ]
            )
        return row

    def _on_pick_zip_files(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        for file in e.files:
            self._zip_paths.add(file.path)
        controls = [ZipPath(path, on_delete=self._delete_path) for path in sorted(self._zip_paths)]
        self._zip_paths_column.controls = controls
        self.update_page()


def start_gui():
    app = ZipArchivePublisherGUI()
    return app


if __name__ == '__main__':
    app = start_gui()

