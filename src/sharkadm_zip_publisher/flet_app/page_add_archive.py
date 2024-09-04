import time

import flet as ft

from sharkadm_zip_publisher.archive_publisher import ArchivePublisher
from sharkadm_zip_publisher.flet_app.utils import fix_url_str
from sharkadm_zip_publisher.zip import ZipPath

from sharkadm import utils as sharkadm_utils

COLOR_DATASETS_MAIN = '#a1c995'


class PageAddArchive(ft.UserControl):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self._zip_paths = set()

    def build(self):
        self._zip_paths_column = ft.Column(tight=True, scroll=ft.ScrollMode.ALWAYS)
        self._option_update_zip_archives = ft.Checkbox(label='Uppdatera zip-paket',
                                                       tooltip='Uppdaterar zip-peketen med _sv-columner. Uppdaterade paket skriver INTE över befintliga.')
        self._option_copy_zip_archives_to_sharkdata = ft.Checkbox(label='Kopiera zip-paket till "datasets"')
        self._option_trigger_dataset_import = ft.Checkbox(label='Importera zip-paketen')
        options_column = ft.Column([
            self._option_update_zip_archives,
            self._option_copy_zip_archives_to_sharkdata,
            self._option_trigger_dataset_import
        ])
        container_paths = ft.Container(bgcolor='#82b2ff',
                                       content=self._zip_paths_column,
                                       expand=True)
        container_options = ft.Container(bgcolor=COLOR_DATASETS_MAIN,
                                         content=options_column)
        self._go_dataset_button = ft.ElevatedButton(text='Kör', on_click=self._run_zip, bgcolor='green')
        col = ft.Column([
            self._get_select_sharkdata_dataset_directory_row(),
            self._get_dataset_pick_url_trigger_row(),
            self._get_pick_zip_files_button(),
            container_paths,
            container_options,
            self._go_dataset_button
        ], expand=True)

        return col

    def _get_select_sharkdata_dataset_directory_row(self) -> ft.Row:

        self._sharkdata_dataset_directory = ft.Text()

        pick_sharkdata_dataset_directory_dialog = ft.FilePicker(on_result=self.on_select_sharkdata_dataset_import_directory)

        self.page.overlay.append(pick_sharkdata_dataset_directory_dialog)
        self._pick_sharkdata_dataset_directory_button = ft.ElevatedButton(
                        "Välj mapp där du vill lägga zip-paketen",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: pick_sharkdata_dataset_directory_dialog.get_directory_path(
                            dialog_title='Välj mapp där du vill lägga zip-paketen',
                            initial_directory=self._sharkdata_dataset_directory.value
                        ))

        row = ft.Row(
                [
                    self._pick_sharkdata_dataset_directory_button,
                    self._sharkdata_dataset_directory
                ]
            )
        return row

    def _get_dataset_pick_url_trigger_row(self) -> ft.Row:
        self._dataset_trigger_url = ft.TextField(multiline=False, label='URL som triggar importen', width=600,
                                         on_blur=self._on_change_dataset_trigger_url)
        self._dataset_status_url = ft.TextField(multiline=False, label='URL som kollar status på importen',
                                        tooltip='Den här sätts automatiskt om trigger-url säts', width=600,
                                        on_blur=self._on_change_dataset_status_url)

        row = ft.Row([ft.Column(
            [
                self._dataset_trigger_url,
                self._dataset_status_url
            ]
        )])
        return row

    def _get_pick_zip_files_button(self) -> ft.Row:
        pick_zip_files_dialog = ft.FilePicker(on_result=self._on_pick_zip_files)

        self.page.overlay.append(pick_zip_files_dialog)
        self._pick_zip_files_button = ft.ElevatedButton(
                        "Välj ett eller flera zip-paket",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: pick_zip_files_dialog.pick_files(
                            allow_multiple=True,
                            allowed_extensions=['zip']
                        ))

        row = ft.Row(
                [
                    self._pick_zip_files_button,
                ]
            )
        return row

    def _on_change_dataset_trigger_url(self, event=None):
        trigger_url = fix_url_str(self._dataset_trigger_url.value)
        self._dataset_trigger_url.value = trigger_url
        self._dataset_trigger_url.update()

        self._dataset_status_url.value = trigger_url + '/status'
        self._dataset_status_url.update()

    def on_select_sharkdata_dataset_import_directory(self, e: ft.FilePickerResultEvent) -> None:
        if not e.path:
            return
        self._sharkdata_dataset_directory.value = e.path
        self._sharkdata_dataset_directory.update()

    def _on_pick_zip_files(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        for file in e.files:
            self._zip_paths.add(file.path)
        controls = [ZipPath(path, on_delete=self._delete_zip_path) for path in sorted(self._zip_paths)]
        self._zip_paths_column.controls = controls
        self.update()

    def _delete_zip_path(self, path_control: ZipPath):
        self._zip_paths_column.controls.remove(path_control)
        self._zip_paths.remove(path_control.path)
        self.update()

    def _on_change_dataset_status_url(self, event=None):
        status_url = fix_url_str(self._dataset_status_url.value)
        self._dataset_status_url.value = status_url
        self._dataset_status_url.update()

    def _enable_buttons(self):
        for btn in [
            self._pick_zip_files_button, self._go_dataset_button,
        ]:
            btn.disabled = False
            btn.update()

    def _disable_buttons(self):
        for btn in [
            self._pick_zip_files_button, self._go_dataset_button,
        ]:
            btn.disabled = True
            btn.update()

    def _run_zip(self, *args):
        if not any([self._option_trigger_dataset_import.value, self._option_update_zip_archives.value, self._option_copy_zip_archives_to_sharkdata.value]):
            self.parent.show_dialog('Du har inte valt något att göra!')
            return
        if not self._zip_paths and any([self._option_update_zip_archives.value, self._option_copy_zip_archives_to_sharkdata.value]):
            self.parent.show_dialog('Inga zip-arkiv valda!')
            return
        if self._option_trigger_dataset_import.value and not all([self._dataset_trigger_url.value.strip(), self._dataset_status_url.value.strip()]):
            self.parent.show_dialog('Du måste fylla i fälten för URL!')
            return

        self._disable_buttons()
        self.parent.export_saves()

        sharkadm_utils.clear_temp_directory()

        publisher = ArchivePublisher(
            sharkdata_dataset_directory=self._sharkdata_dataset_directory.value,
            trigger_url=self._dataset_trigger_url.value,
            import_url=self._dataset_status_url.value
        )

        for path in self._zip_paths:
            publisher.set_zip_archive_paths(path)
            if self._option_update_zip_archives.value:
                self.parent.show_dialog(f'Uppdaterar {path}...')
                publisher.update_zip_archives()
            if self._option_copy_zip_archives_to_sharkdata.value:
                self.parent.show_dialog(f'Kopierar {path}...')
                publisher.copy_archives_to_sharkdata()
        if self._option_trigger_dataset_import.value:
            self.parent.show_dialog(f'Triggar import...')
            publisher.trigger_import()
            time.sleep(1)
        self.parent.show_dialog(f'Allt klart!')
        # self._export_saves()
        self._enable_buttons()
