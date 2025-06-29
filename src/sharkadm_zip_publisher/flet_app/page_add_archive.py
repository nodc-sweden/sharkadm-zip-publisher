import pathlib

import flet as ft
from sharkadm import utils as sharkadm_utils
from sharkadm.sharkadm_logger import create_xlsx_report, adm_logger

from sharkadm_zip_publisher.archive_publisher import ArchivePublisher
from sharkadm_zip_publisher.flet_app import utils
from sharkadm_zip_publisher.flet_app.constants import COLOR_DATASETS_MAIN
from sharkadm_zip_publisher.flet_app.saves import publisher_saves
from sharkadm_zip_publisher.zip import ZipPath
from sharkadm import sharkadm_exceptions

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sharkadm_zip_publisher.flet_app.app import ZipArchivePublisherGUI


class PageAddArchive(ft.Row):

    def __init__(self, main_app: 'ZipArchivePublisherGUI'):
        super().__init__()
        self.main_app: 'ZipArchivePublisherGUI' = main_app
        self._zip_paths = set()
        self._run = None

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
        self._abort_button = ft.ElevatedButton(text='Avbryt', on_click=self._abort)
        self._abort_button.disabled = True

        self._nr_zip_packages = ft.Text('Inga paket valda')

        col = ft.Column([
            ft.Divider(height=9, thickness=3),
            ft.Row([
                self._get_pick_zip_files_button(),
                ft.IconButton(
                    icon=ft.icons.DELETE_FOREVER_ROUNDED,
                    icon_color=COLOR_DATASETS_MAIN,
                    icon_size=40,
                    tooltip="Rensa listan",
                    on_click=self._delete_all_zip_paths
                ),
                self._nr_zip_packages
            ]),
            container_paths,
            container_options,
            ft.Row([
                self._go_dataset_button,
                self._abort_button,
            ]),
        ], expand=True)

        return col

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

    def _abort(self, *args):
        msg = 'Avbryter körning...'
        self.main_app.show_info(msg)
        self._abort_button.text = msg
        self._abort_button.update()
        self._run = False

    def _reset_abort_button(self) -> None:
        self._abort_button.text = 'Avbryt'
        self._abort_button.update()

    def _on_pick_zip_files(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        for file in e.files:
            self._zip_paths.add(file.path)
        controls = [ZipPath(path, on_delete=self._delete_zip_path) for path in sorted(self._zip_paths)]
        self._zip_paths_column.controls = controls
        self._set_nr_zip_paths()
        self.update()

    def _delete_zip_path(self, path_control: ZipPath):
        self._zip_paths_column.controls.remove(path_control)
        self._zip_paths.remove(path_control.path)
        self._set_nr_zip_paths()
        self.update()

    def _delete_all_zip_paths(self, event=None):
        self._zip_paths_column.controls = []
        self._zip_paths = set()
        self._set_nr_zip_paths()
        self.update()

    def _set_nr_zip_paths(self):
        nr = len(self._zip_paths)
        text = 'Inga valda paket'
        if nr == 1:
            text = f'{nr} paket valt'
        elif nr:
            text = f'{nr} paket valda'
        self._nr_zip_packages.value = text
        self._nr_zip_packages.update()

    def _enable_buttons(self):
        for btn in [
            self._pick_zip_files_button, self._go_dataset_button,
        ]:
            btn.disabled = False
            btn.update()
        self._abort_button.disabled = True
        self._abort_button.text = 'Avbryt'
        self._abort_button.update()

    def _disable_buttons(self):
        for btn in [
            self._pick_zip_files_button, self._go_dataset_button,
        ]:
            btn.disabled = True
            btn.update()
        self._abort_button.disabled = False
        self._abort_button.text = 'Avbryt'
        self._abort_button.update()

    def _run_zip(self, *args):
        try:
            if not any([self._option_trigger_dataset_import.value, self._option_update_zip_archives.value,
                        self._option_copy_zip_archives_to_sharkdata.value]):
                self.main_app.show_dialog('Du har inte valt något att göra!')
                return
            if not self._zip_paths and any(
                    [self._option_update_zip_archives.value, self._option_copy_zip_archives_to_sharkdata.value]):
                self.main_app.show_dialog('Inga zip-arkiv valda!')
                return
            if self._zip_paths and self._option_copy_zip_archives_to_sharkdata.value and not self.main_app.datasets_directory:
                self.main_app.show_dialog('Inga mapp för att lägga remove.txt vald!')
                return
            if self._option_trigger_dataset_import.value and not all(
                    [self.main_app.trigger_url, self.main_app.status_url]):
                self.main_app.show_dialog('Du måste fylla i fälten för URL!')
                return

            self._disable_buttons()
            publisher_saves.export_saves()

            # sharkadm_utils.clear_temp_directory()
            sharkadm_utils.clear_all_in_temp_directory()

            publisher = ArchivePublisher(
                sharkdata_dataset_directory=self.main_app.datasets_directory,
                zip_directory=self.main_app.zip_directory,
                trigger_url=self.main_app.trigger_url,
                import_url=self.main_app.status_url,
                restrict_data=self.main_app.restrict_data,
            )

        except Exception as e:
            self.main_app.show_dialog(f'Något gick fel:\n{e}')
            self._enable_buttons()
            raise

        if self.main_app.env.upper() == 'TEST':
            self._run_zip_test(publisher)
        elif self.main_app.env.upper() == 'PROD':
            self._run_zip_other(publisher)
            self._change_env_with_same_options('UTVTST')
            dev_publisher = ArchivePublisher(
                sharkdata_dataset_directory=self.main_app.datasets_directory,
                zip_directory=self.main_app.zip_directory,
                trigger_url=self.main_app.trigger_url,
                import_url=self.main_app.status_url,
                restrict_data=False,
            )
            self._run_zip_other(dev_publisher)
            self._change_env_with_same_options('PROD')
        else:
            self._run_zip_other(publisher)

    def _change_env_with_same_options(self, env: str):
        option_update = self._option_update_zip_archives.value
        option_copy = self._option_copy_zip_archives_to_sharkdata.value
        option_trigger_import = self._option_trigger_dataset_import.value
        self.main_app.change_env(env)
        self._option_update_zip_archives.value = option_update
        self._option_copy_zip_archives_to_sharkdata.value = option_copy
        self._option_trigger_dataset_import.value = option_trigger_import
        self._option_update_zip_archives.update()
        self._option_copy_zip_archives_to_sharkdata.update()
        self._option_trigger_dataset_import.update()

    def _do_publish_stuff(self, publisher: ArchivePublisher, path: pathlib.Path) -> list:
        publish_not_allowed = []
        p = pathlib.Path(path)
        publisher.set_zip_archive_paths(path)
        if self._option_update_zip_archives.value:
            self.main_app.show_info(f'Uppdaterar {path}...')
            info = publisher.update_zip_archives()
            publish_not_allowed = info.get('publish_not_allowed')
        if self._option_copy_zip_archives_to_sharkdata.value:
            if publisher.publish_is_allowed(p.name, allow_all=False):
                self.main_app.show_info(f'Kopierar {path}...')
            publisher.copy_archives_to_sharkdata(allow_all=False)
        return publish_not_allowed

    def _trigger_and_copy(self):
        if self._option_trigger_dataset_import.value:
            self.main_app.trigger_import()
        if self._option_copy_zip_archives_to_sharkdata.value:
            self.main_app.show_info(f'Trying to delete everything in temp directory: {sharkadm_utils.TEMP_DIRECTORY}')
            sharkadm_utils.clear_all_in_temp_directory()

    def _log_publish_not_allowed(self, publish_not_allowed: set):
        if not publish_not_allowed:
            return
        self.main_app.log_workflow(dict(msg=''))
        self.main_app.log_workflow(dict(msg='Not allowed to publish the following packages:'))
        for name in publish_not_allowed:
            self.main_app.log_workflow(dict(msg=f'    {name}'))

    def _run_zip_test(self, publisher: ArchivePublisher):
        failing_zips = []
        publish_not_allowed = set()
        self._run = True
        tot_nr = len(self._zip_paths)
        nr = 0
        for nr, path in enumerate(sorted(self._zip_paths)):
            if not self._run:
                break
            if not nr % 20:
                sharkadm_utils.clear_all_in_temp_directory()
            p = pathlib.Path(path)
            try:
                p_not_allowed = self._do_publish_stuff(publisher, path)
                publish_not_allowed.update(p_not_allowed)
            except sharkadm_exceptions.SHARKadmException as e:
                failing_zips.append(f'{p.name} -> {e}')
                raise
            except Exception as e:
                failing_zips.append(f'{p.name} -> {e}')
                self.main_app.log_workflow(dict(
                    level='warning', msg=f'FEL I PAKET (ej hanterat av SHARKadm) {pathlib.Path(path).name}: {e}'
                ))
                raise
            finally:
                pass
        self._trigger_and_copy()
        self._create_reports()
        self._enable_buttons()
        self._log_publish_not_allowed(publish_not_allowed)
        if not self._run:
            # sharkadm_utils.clear_all_in_temp_directory()
            self.main_app.show_dialog(f'Körningen avbruten av användaren ({nr} av {tot_nr} körda)!')
        elif failing_zips:
            start_text = '1 felaktigt paket.'
            if len(failing_zips) > 1:
                start_text = f'{len((failing_zips))} felaktiga paket.'
            self.main_app.show_dialog(f'{start_text} Se log för detaljer!')
            self.main_app.log_workflow(dict(msg=''))
            self.main_app.log_workflow(dict(msg='Could not handle the following packages'))
            for info in failing_zips:
                self.main_app.log_workflow(dict(msg=f'    {info}'))
        else:
            self.main_app.show_dialog('Allt klart!')

    def _run_zip_other(self, publisher: ArchivePublisher):
        publish_not_allowed = set()
        try:
            self._run = True
            tot_nr = len(self._zip_paths)
            nr = 0
            for nr, path in enumerate(sorted(self._zip_paths)):
                if not self._run:
                    break
                self.main_app.update_progress(
                    dict(
                        title=f"Arbetar med paket {pathlib.Path(path).name}",
                        current=nr + 1,
                        total=tot_nr
                    )
                )
                import time
                time.sleep(2)
                if not nr % 20:
                    sharkadm_utils.clear_all_in_temp_directory()
                p_not_allowed = self._do_publish_stuff(publisher, path)
                publish_not_allowed.update(p_not_allowed)
            self._trigger_and_copy()
            self._create_reports()
            self._enable_buttons()
            self._log_publish_not_allowed(publish_not_allowed)
            if not self._run:
                sharkadm_utils.clear_all_in_temp_directory()
                self.main_app.show_dialog(f'Körningen avbruten av användaren ({nr} av {tot_nr} körda)!')
            else:
                self.main_app.show_dialog('Allt klart!')
        except Exception as e:
            self.main_app.show_dialog(f'Något gick fel:\n{e}')
            self._enable_buttons()
            raise
        finally:
            self.main_app.reset_progress()
            self._enable_buttons()

    def _create_reports(self) -> None:
        create_xlsx_report(adm_logger.reset_filter(), export_directory=utils.LOG_DIRECTORY)
        create_xlsx_report(adm_logger.reset_filter().filter('>warning', 'transformation'),
                           export_directory=utils.LOG_DIRECTORY, tag='transformation')
        create_xlsx_report(adm_logger.reset_filter().filter('>info', 'validation'),
                           export_directory=utils.LOG_DIRECTORY, tag='validation')
