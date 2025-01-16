import pathlib

import flet as ft

from sharkadm_zip_publisher.archive_remover import ArchiveRemover
from sharkadm_zip_publisher.flet_app.constants import COLOR_DATASETS_REMOVE, COLOR_DATASETS_MAIN
from sharkadm_zip_publisher.flet_app.saves import publisher_saves
from sharkadm_zip_publisher.zip import ZipPath


class PageRemoveArchive(ft.UserControl):

    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self._remove_zip_names = set()

    def build(self):
        self._remove_zip_names_column = ft.Column(tight=True, scroll=ft.ScrollMode.ALWAYS)
        self._option_create_remove_file = ft.Checkbox(label='Skapa remove.txt-fil')
        self._option_trigger_remove_file = ft.Checkbox(label='Ta bort paket (trigga import API)')
        options_column = ft.Column([
            self._option_create_remove_file,
            self._option_trigger_remove_file,
        ])
        container_paths = ft.Container(bgcolor=COLOR_DATASETS_REMOVE,
                                       content=self._remove_zip_names_column,
                                       expand=True)
        container_options = ft.Container(bgcolor=COLOR_DATASETS_REMOVE,
                                         content=options_column)
        self._go_remove_dataset_button = ft.ElevatedButton(text='Kör', on_click=self._run_remove_zip, bgcolor='green')
        col = ft.Column([
            # self._get_select_sharkdata_remove_dataset_directory_row(),
            ft.Divider(height=9, thickness=3, color=COLOR_DATASETS_REMOVE),
            self._get_row_add_dataset_to_remove(),
            ft.Row([
                self._get_pick_remove_zip_files_button(),
                ft.IconButton(
                    icon=ft.icons.DELETE_FOREVER_ROUNDED,
                    icon_color=COLOR_DATASETS_MAIN,
                    icon_size=40,
                    tooltip="Rensa listan",
                    on_click=self._delete_all_remove_zip_paths
                ),
            ]),
            container_paths,
            container_options,
            self._go_remove_dataset_button
        ], expand=True)

        return col

    def _enable_buttons(self):
        for btn in [
            self._pick_remove_zip_files_button, self._go_remove_dataset_button,
        ]:
            btn.disabled = False
            btn.update()

    def _disable_buttons(self):
        for btn in [
            self._pick_remove_zip_files_button, self._go_remove_dataset_button,
        ]:
            btn.disabled = True
            btn.update()

    def _get_row_add_dataset_to_remove(self) -> ft.Row:
        self._textfield_zip_to_remove = ft.TextField(label='Ange zip-paket du vill ta bort',
                                                     on_submit=self._add_zip_to_remove_from_textfield,
                                                     width=600)
        btn = ft.ElevatedButton(text='Lägg till i listan',
                                on_click=self._add_zip_to_remove_from_textfield)

        return ft.Row([self._textfield_zip_to_remove, btn])

    def _get_pick_remove_zip_files_button(self) -> ft.Row:
        pick_remove_zip_files_dialog = ft.FilePicker(on_result=self._on_pick_remove_zip_files)

        self.page.overlay.append(pick_remove_zip_files_dialog)
        self._pick_remove_zip_files_button = ft.ElevatedButton(
                        "Välj ett eller flera zip-paket som du vill ta bort",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: pick_remove_zip_files_dialog.pick_files(
                            allow_multiple=True,
                            allowed_extensions=['zip']
                        ))

        row = ft.Row(
                [
                    self._pick_remove_zip_files_button,
                ]
            )
        return row

    def _run_remove_zip(self, *args):
        try:
            if not any([self._option_create_remove_file.value, self._option_trigger_remove_file.value]):
                self.main_app.show_dialog('Du har inte valt något att göra!')
                return
            if not self._remove_zip_names and self._option_create_remove_file.value:
                self.main_app.show_dialog('Inga zip-arkiv valda för borttagning!')
                return

            if self._remove_zip_names and self._option_create_remove_file.value and not self.main_app.datasets_directory:
                self.main_app.show_dialog('Inga mapp för att lägga remove.txt vald!')
                return

            if self._option_trigger_remove_file.value and not all([self.main_app.trigger_url, self.main_app.status_url]):
                self.main_app.show_dialog('Du måste fylla i fälten för URL!')
                return
            self._disable_buttons()
            publisher_saves.export_saves()

            publisher = ArchiveRemover(
                sharkdata_datasets_directory=self.main_app.datasets_directory,
                trigger_url=self.main_app.trigger_url,
                import_url=self.main_app.status_url)

            self._do_stuff(publisher)
            if self.main_app.env.upper() == 'PROD':
                self._change_env_with_same_options('UTV')
                dev_publisher = ArchiveRemover(
                    sharkdata_datasets_directory=self.main_app.datasets_directory,
                    trigger_url=self.main_app.trigger_url,
                    import_url=self.main_app.status_url
                )
                self._do_stuff(dev_publisher)
                self._change_env_with_same_options('PROD')

            self._enable_buttons()
            self.main_app.show_dialog('Allt klart!')
        except Exception as e:
            self.main_app.show_dialog(f'Något gick fel:\n{e}')
            raise

    def _do_stuff(self, publisher: ArchiveRemover) -> None:
        if self._option_create_remove_file.value:
            publisher.set_remove_names(list(self._remove_zip_names))
            publisher.create_remove_file()
        if self._option_trigger_remove_file.value:
            self.main_app.trigger_import()

    def _change_env_with_same_options(self, env: str):
        option_copy = self._option_create_remove_file.value
        option_trigger_import = self._option_trigger_remove_file.value
        self.main_app.change_env(env)
        self._option_create_remove_file.value = option_copy
        self._option_trigger_remove_file.value = option_trigger_import
        self._option_create_remove_file.update()
        self._option_trigger_remove_file.update()

    def _on_pick_remove_zip_files(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        for file in e.files:
            self._remove_zip_names.add(pathlib.Path(file.path).name)
        controls = [ZipPath(path, on_delete=self._delete_remove_zip_path) for path in sorted(self._remove_zip_names)]
        self._remove_zip_names_column.controls = controls
        self.update()

    def _add_zip_to_remove_from_textfield(self, event=None):
        value = self._textfield_zip_to_remove.value.strip()
        if not value:
            self.main_app.show_dialog('Inget valt för borttagning')
            return
        self._add_remove_zip_names(value)
        self._textfield_zip_to_remove.value = ''
        self._textfield_zip_to_remove.update()

    def _add_remove_zip_names(self, *names: str):
        current_controls = self._remove_zip_names_column.controls
        self._remove_zip_names = sorted(set(([cont.path for cont in current_controls] + list(names))))
        controls = [ZipPath(path, on_delete=self._delete_remove_zip_path) for path in self._remove_zip_names]
        self._remove_zip_names_column.controls = sorted(controls, key=lambda x: x.path)
        self.update()

    def _delete_remove_zip_path(self, path_control: ZipPath):
        self._remove_zip_names_column.controls.remove(path_control)
        self._remove_zip_names.remove(pathlib.Path(path_control.path).name)
        self.update()

    def _delete_all_remove_zip_paths(self, event=None):
        self._remove_zip_names_column.controls = []
        self._remove_zip_names = set()
        self.update()