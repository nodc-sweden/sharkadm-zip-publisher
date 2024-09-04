import pathlib
import shutil

import requests
from sharkadm import transformers, controller, exporters, adm_logger, utils
from sharkadm.data import get_zip_archive_data_holder

from sharkadm_zip_publisher.exceptions import ImportNotAvailable


class ArchivePublisher:

    def __init__(self,
                 sharkdata_dataset_directory=None,
                 trigger_url=None,
                 import_url=None
                 ):
        self._config = dict(
            sharkdata_dataset_directory=sharkdata_dataset_directory,
            url_trigger_import=trigger_url,
            url_import_status=import_url
        )
        if not all(list(self._config.values())):
            raise Exception('Missing input parameters!')

        self._zip_archive_paths: list[pathlib.Path] = []
        self._transformers: list[transformers.Transformer] = []
        self._updated_zip_archive_paths: list[pathlib.Path] = []

        self._controller = controller.SHARKadmController()

        self._create_transformers()

    @property
    def zip_archive_paths(self):
        return self._updated_zip_archive_paths or self._zip_archive_paths

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
            print(f'update_zip_archives: {encoding=}')

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