import os
import pathlib
import shutil

from sharkadm import transformers, controller, exporters, adm_logger
from sharkadm import utils as sharkadm_utils
from sharkadm.data import get_zip_archive_data_holder
from sharkadm_zip_publisher import restrict

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

    def _package_is_ok_to_publish(self, data_holder) -> bool:
        if not restrict.RESTRICT_DATA:
            return True
        if data_holder.data_type not in restrict.SKIP_DATA_TYPES:
            return True
        for pack in restrict.INCLUDE_PACKAGES:
            if pack.upper() in data_holder.zip_archive_path.name.upper():
                return True
        adm_logger.log_workflow(
            f'Not allowed to publish package of data type {data_holder.data_type}: {data_holder.zip_archive_path.name}',
            level=adm_logger.INFO)

    def _restrict_data_holder(self, data_holder) -> None:
        if not restrict.RESTRICT_DATA:
            return
        data_holder.remove_processed_data_directory()
        data_holder.remove_received_data_directory()
        data_holder.remove_readme_files()
        files_left = data_holder.list_files()
        if len(files_left) != 3:
            adm_logger.log_workflow(f'More than 3 expected files left in the restricted zip package: {sorted(files_left)}', level=adm_logger.WARNING)

    def update_zip_archives(self) -> dict:
        self._updated_zip_archive_paths = []
        publish_not_allowed = []
        for path in self._zip_archive_paths:
            data_holder = get_zip_archive_data_holder(path)
            if not self._package_is_ok_to_publish(data_holder):
                publish_not_allowed.append(f'{path.name} (data type {data_holder.data_type} not allowed)')
                continue
            self._controller.set_data_holder(data_holder)
            self._run_transformers()
            encoding = 'cp1252'
            exporter = exporters.SHARKdataTxtAsGiven(encoding=encoding,
                                                     export_directory=data_holder.unzipped_archive_directory,
                                                     export_file_name=data_holder.unzipped_archive_directory / 'shark_data.txt')
            adm_logger.log_workflow(f'Encoding is {encoding} for package {path}', level=adm_logger.DEBUG)

            self._controller.export(exporter)
            self._restrict_data_holder(data_holder)
            rezipped_archive_path = self._zip_directory(data_holder.unzipped_archive_directory)
            self._updated_zip_archive_paths.append(pathlib.Path(rezipped_archive_path))
        return dict(
            publish_not_allowed=publish_not_allowed,
        )

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
    def transformers(self) -> list[transformers.Transformer]:
        return self._transformers

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
            transformers.FixTimeFormat(),
            transformers.AddReportedDates(),
            transformers.AddSampleDate(),
            transformers.CreateFakeFullDates(),
            transformers.ManualSealPathology(),
            transformers.ManualHarbourPorpoise(),
            ]

        if restrict.RESTRICT_DATA:
            self._transformers.extend([
                transformers.RemoveValuesInColumns(*restrict.DEPTH_COLUMNS, replace_value=restrict.DEPTH_REPLACE_VALUE),
                transformers.RemoveValuesInColumns(*restrict.SECCHI_COLUMNS, replace_value=restrict.SECCHI_REPLACE_VALUE),
                transformers.RemoveValuesInColumns(*restrict.COMMENT_COLUMNS, replace_value=restrict.COMMENT_REPLACE_VALUE),

                transformers.RemoveRowsForParameters(*restrict.REMOVE_PARAMETER_ROWS),

                transformers.RemoveDeepestDepthAtEachVisit(
                    valid_data_types=['PhysicalChemical'],
                    depth_column='sample_depth_m',
                    also_remove_from_columns=['sample_id', 'shark_sample_id'],
                    replace_value=restrict.DEPTH_REPLACE_VALUE
                ),
            ])
            for col in ['sample_depth_m', 'sample_min_depth_m', 'sample_max_depth_m']:
                self._transformers.append(transformers.RemoveDeepestDepthAtEachVisit(
                    valid_data_types=['Bacterioplankton', 'Harbourporpoise'],
                    depth_column=col,
                    also_remove_from_columns=['sample_id', 'shark_sample_id'],
                    replace_value=restrict.DEPTH_REPLACE_VALUE
                ))

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
