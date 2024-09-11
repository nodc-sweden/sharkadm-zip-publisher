import time

import flet as ft
from sharkadm import utils as sharkadm_utils

from sharkadm_zip_publisher.config_publisher import ConfigPath, ConfigPublisher
from sharkadm_zip_publisher.flet_app.constants import COLOR_CONFIG_MAIN, COLOR_DATASETS_MAIN
from sharkadm_zip_publisher.flet_app.saves import publisher_saves


class PageConfig(ft.UserControl):

    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
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
            ft.Divider(height=9, thickness=3),
            ft.Row([
                self._get_pick_config_files_button(),
                ft.IconButton(
                    icon=ft.icons.DELETE_FOREVER_ROUNDED,
                    icon_color=COLOR_DATASETS_MAIN,
                    icon_size=40,
                    tooltip="Rensa listan",
                    on_click=self._delete_all_config_paths
                ),
            ]),
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

    def _delete_config_path(self, path_control: ConfigPath):
        self._config_paths_column.controls.remove(path_control)
        self._config_paths.remove(path_control.path)
        self.update()

    def _delete_all_config_paths(self, event=None):
        self._config_paths_column.controls = []
        self._config_paths = set()
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
        try:
            if not any([self._option_trigger_config_import.value,
                        self._option_copy_config_to_sharkdata.value]):
                self.main_app.show_dialog('Du har inte valt något att göra!')
                return
            if not self._config_paths and self._option_copy_config_to_sharkdata.value:
                self.main_app.show_dialog('Inga config-filer valda!')
                return
            if self._option_trigger_config_import.value and not all([self.main_app.trigger_url.value.strip(),
                                                                      self.main_app.status_url.value.strip()]):
                self.main_app.show_dialog('Du måste fylla i fälten för URL!')
                return
            self._disable_buttons()
            publisher_saves.export_saves()

            sharkadm_utils.clear_temp_directory()

            publisher = ConfigPublisher(
                sharkdata_config_directory=self._sharkdata_config_directory.value,
                trigger_url=self.main_app.trigger_url,
                import_url=self.main_app.status_url
            )

            if self._option_copy_config_to_sharkdata.value:
                publisher.set_config_paths(list(self._config_paths))
                publisher.copy_config_files_to_sharkdata()

            if self._option_trigger_config_import.value:
                self.main_app.show_info(f'Triggar import...')
                publisher.trigger_import()
                time.sleep(1)
            self.main_app.show_dialog(f'Allt klart!')
            self._enable_buttons()
        except Exception as e:
            self.main_app.show_dialog(f'Något gick fel:\n{e}')
            raise


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
