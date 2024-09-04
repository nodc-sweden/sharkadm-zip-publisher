import pathlib
import time

import flet as ft

from sharkadm_zip_publisher.archive_publisher import ArchivePublisher
from sharkadm_zip_publisher.archive_remover import ArchiveRemover
from sharkadm_zip_publisher.config_publisher import ConfigPath, ConfigPublisher
from sharkadm_zip_publisher.flet_app.utils import fix_url_str
from sharkadm_zip_publisher.zip import ZipPath

from sharkadm import utils as sharkadm_utils

COLOR_CONFIG_MAIN = '#f9c995'


class PageConfig(ft.UserControl):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self._config_paths = set()

    def build(self):
        self._config_paths_column = ft.Column(tight=True, scroll=ft.ScrollMode.ALWAYS)
        self._option_copy_config_to_sharkdata = ft.Checkbox(label='Kopiera config-filer till "configs"')
        self._option_trigger_config_import = ft.Checkbox(label='Importera config--filer')
        options_column = ft.Column([
            self._option_copy_config_to_sharkdata,
            self._option_trigger_config_import
        ])
        container_paths = ft.Container(bgcolor='#82b2ff',
                                       content=self._config_paths_column,
                                       expand=True)
        container_options = ft.Container(bgcolor=COLOR_CONFIG_MAIN,
                                         content=options_column)

        self._go_config_button = ft.ElevatedButton(text='Kör', on_click=self._run_config, bgcolor='green')
        col = ft.Column([
            self._get_select_sharkdata_config_directory_row(),
            self._get_config_pick_url_trigger_row(),
            self._get_pick_config_files_button(),
            container_paths,
            container_options,
            self._go_config_button
        ], expand=True)

        return col

    def _get_select_sharkdata_config_directory_row(self) -> ft.Row:

        self._sharkdata_config_directory = ft.Text()

        pick_sharkdata_config_directory_dialog = ft.FilePicker(on_result=self.on_select_sharkdata_config_import_directory)

        self.page.overlay.append(pick_sharkdata_config_directory_dialog)
        self._pick_sharkdata_config_directory_button = ft.ElevatedButton(
                        "Välj mapp där du vill lägga config-filerna",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: pick_sharkdata_config_directory_dialog.get_directory_path(
                            dialog_title='Välj mapp där du vill lägga config-filerna',
                            initial_directory=self._sharkdata_config_directory.value
                        ))

        row = ft.Row(
                [
                    self._pick_sharkdata_config_directory_button,
                    self._sharkdata_config_directory
                ]
            )
        return row

    def _get_config_pick_url_trigger_row(self) -> ft.Row:
        self._config_trigger_url = ft.TextField(multiline=False,
                                                label='URL som triggar importen',
                                                width=600, on_blur=self._on_change_config_trigger_url)
        self._config_status_url = ft.TextField(multiline=False,
                                               label='URL som kollar status på importen',
                                               tooltip='Den här sätts automatiskt om trigger-url säts',
                                               width=600,
                                               on_blur=self._on_change_config_status_url)

        row = ft.Row([ft.Column(
                [
                    self._config_trigger_url,
                    self._config_status_url
                ]
            )])
        return row

    def _delete_config_path(self, path_control: ConfigPath):
        self._config_paths_column.controls.remove(path_control)
        self._config_paths.remove(path_control.path)
        self.update()

    def _get_pick_config_files_button(self) -> ft.Row:
        pick_config_files_dialog = ft.FilePicker(on_result=self._on_pick_config_files)

        self.page.overlay.append(pick_config_files_dialog)
        self._pick_config_files_button = ft.ElevatedButton(
            "Välj ett eller flera config-filer",
            icon=ft.icons.UPLOAD_FILE,
            on_click=lambda _: pick_config_files_dialog.pick_files(
                allow_multiple=True,
                allowed_extensions=['csv', 'dbf', 'prj', 'qix', 'sbn', 'sbx', 'shp', 'shx', 'txt', 'xml']
            ))

        row = ft.Row(
            [
                self._pick_config_files_button,
            ]
        )
        return row

    def _on_change_config_trigger_url(self, event=None):
        trigger_url = fix_url_str(self._config_trigger_url.value)
        self._config_trigger_url.value = trigger_url
        self._config_trigger_url.update()

        self._config_status_url.value = trigger_url + '/status'
        self._config_status_url.update()

    def _on_change_config_status_url(self, event=None):
        status_url = fix_url_str(self._config_status_url.value)
        self._config_status_url.value = status_url
        self._config_status_url.update()

    def _on_pick_config_files(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        for file in e.files:
            self._config_paths.add(file.path)
        controls = [ConfigPath(path, on_delete=self._delete_config_path) for path in sorted(self._config_paths)]
        self._config_paths_column.controls = controls
        self.update()

    def on_select_sharkdata_config_import_directory(self, e: ft.FilePickerResultEvent) -> None:
        if not e.path:
            return
        self._sharkdata_config_directory.value = e.path
        self._sharkdata_config_directory.update()

    def _run_config(self, *args):
        if not any([self._option_trigger_config_import.value,
                    self._option_copy_config_to_sharkdata.value]):
            self.parent.show_dialog('Du har inte valt något att göra!')
            return
        if not self._config_paths and self._option_copy_config_to_sharkdata.value:
            self.parent.show_dialog('Inga config-filer valda!')
            return
        if self._option_trigger_config_import.value and not all([self._config_trigger_url.value.strip(),
                                                                  self._config_status_url.value.strip()]):
            self.parent.show_dialog('Du måste fylla i fälten för URL!')
            return
        self._disable_buttons()
        self.parent.export_saves()

        sharkadm_utils.clear_temp_directory()

        publisher = ConfigPublisher(
            sharkdata_config_directory=self._sharkdata_config_directory.value,
            trigger_url=self._config_trigger_url.value,
            import_url=self._config_status_url.value
        )

        if self._option_copy_config_to_sharkdata.value:
            publisher.set_config_paths(list(self._config_paths))
            publisher.copy_config_files_to_sharkdata()

        if self._option_trigger_config_import.value:
            self.parent.show_dialog(f'Triggar import...')
            publisher.trigger_import()
            time.sleep(1)
        self.parent.show_dialog(f'Allt klart!')
        self._enable_buttons()

    def _enable_buttons(self):
        for btn in [
            self._pick_config_files_button, self._go_config_button
        ]:
            btn.disabled = False
            btn.update()

    def _disable_buttons(self):
        for btn in [
            self._pick_config_files_button, self._go_config_button
        ]:
            btn.disabled = True
            btn.update()
