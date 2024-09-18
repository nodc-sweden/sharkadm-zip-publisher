import os
import pathlib
import shutil

from sharkadm import transformers, controller, exporters, adm_logger
from sharkadm import utils as sharkadm_utils
from sharkadm.data import get_zip_archive_data_holder

from sharkadm_zip_publisher.trigger import Trigger

from sharkadm_zip_publisher import utils


class ArchivePublisher(Trigger):

    def __init__(self,
                 sharkdata_dataset_directory=None,
                 zip_directory=None,
                 trigger_url=None,
                 import_url=None
                 ):
        self._config = dict(
            sharkdata_dataset_directory=sharkdata_dataset_directory,
            zip_directory=zip_directory,
            trigger_url=trigger_url,
            status_url=import_url
        )
        super().__init__(**self._config)

        self._zip_archive_paths: list[pathlib.Path] = []
        self._transformers: list[transformers.Transformer] = []
        self._updated_zip_archive_paths: list[pathlib.Path] = []

        self._controller = controller.SHARKadmController()

        self._create_transformers()

    @property
    def zip_archive_paths(self):
        return sorted(self._updated_zip_archive_paths) or sorted(self._zip_archive_paths)

    def update_zip_archives(self):
        self._updated_zip_archive_paths = []
        for path in self._zip_archive_paths:
            data_holder = get_zip_archive_data_holder(path)
            self._controller.set_data_holder(data_holder)
            self._run_transformers()
            encoding = 'cp1252'
            exporter = exporters.SHARKdataTxtAsGiven(encoding=encoding,
                                                     export_directory=data_holder.unzipped_archive_directory,
                                                     export_file_name=data_holder.unzipped_archive_directory / 'shark_data.txt')
            adm_logger.log_workflow(f'Encoding is {encoding} for package {path}')

            self._controller.export(exporter)
            rezipped_archive_path = self._zip_directory(data_holder.unzipped_archive_directory)
            self._updated_zip_archive_paths.append(pathlib.Path(rezipped_archive_path))

    def copy_archives_to_sharkdata(self):
        self._copy_archives_to_sharkdata()
        self._copy_archives_to_zip_directory()

    def _copy_archives_to_sharkdata(self):
        target_root = pathlib.Path(self._config['sharkdata_dataset_directory'])
        for source_path in self.zip_archive_paths:
            target_path = target_root / source_path.name
            shutil.copy2(source_path, target_path)

    def _copy_archives_to_zip_directory(self):
        if not self._config['zip_directory']:
            adm_logger.log_workflow(f'No zip_directory given. Could not copy "locally"!')
            return
        target_root = pathlib.Path(self._config['zip_directory'])
        if not target_root.exists():
            adm_logger.log_workflow(f'Invalid zip_directory: {target_root}')
            return

        current_mapped_zips = utils.get_zip_name_path_mapping(target_root)
        zips_to_remove = []
        zips_to_copy = []
        for source_path in self.zip_archive_paths:
            source_name_no_date = utils.get_zip_name_without_date(source_path.stem)
            current_zip = current_mapped_zips.get(source_name_no_date)
            if current_zip:
                zips_to_remove.append(current_zip)
            target_path = target_root / source_path.name
            zips_to_copy.append((source_path, target_path))

        # Remove old zips
        for path in zips_to_remove:
            adm_logger.log_workflow(f'Removing old package: {path}')
            os.remove(path)

        # Copy new zips
        for source_path, target_path in zips_to_copy:
            shutil.copy2(source_path, target_path)

    @property
    def sharkdata_dataset_directory(self) -> str:
        return self._config['sharkdata_dataset_directory']

    def _create_transformers(self):
        self._transformers = [
            transformers.AddSwedishProjectName(),
            transformers.AddSwedishSampleOrderer(),
            transformers.AddSwedishSamplingLaboratory(),
            transformers.AddSwedishAnalyticalLaboratory(),
            transformers.AddSwedishReportingInstitute(),
            transformers.AddReportedDates(),
            transformers.AddSampleDate(),
            transformers.CreateFakeFullDates()
        ]

    def _run_transformers(self):
        for trans in self._transformers:
            self._controller.transform(trans)

    def _zip_directory(self, directory: pathlib.Path):
        output_filename = sharkadm_utils.get_temp_directory('rezipped_archives') / directory.name
        return shutil.make_archive(str(output_filename), 'zip', str(directory))

    def set_zip_archive_paths(self, *args):
        self._zip_archive_paths = []
        for arg in args:
            path = pathlib.Path(arg)
            if not path.exists():
                raise FileNotFoundError(path)
            self._zip_archive_paths.append(path)
