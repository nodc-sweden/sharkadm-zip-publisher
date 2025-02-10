import os
import pathlib
import shutil

from sharkadm import transformers, controller, exporters, adm_logger, validators
from sharkadm import utils as sharkadm_utils
from sharkadm.data import get_zip_archive_data_holder
from sharkadm.utils import data_filter

from sharkadm_zip_publisher import restrict
from sharkadm_zip_publisher import utils
from sharkadm_zip_publisher.trigger import Trigger


class ArchivePublisher(Trigger):

    def __init__(self,
                 sharkdata_dataset_directory=None,
                 zip_directory=None,
                 trigger_url=None,
                 import_url=None,
                 restrict_data=None,  # If None restriction is decided from restrict.RESTRICT_DATA
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
        self._restricted_transformers: list[transformers.Transformer] = []
        self._validators_after: list[validators.Validator] = []
        self._updated_zip_archive_paths: list[pathlib.Path] = []
        self._publish_not_allowed_packs: list[pathlib.Path] = []

        self._restrict_data = restrict_data

        self._controller = controller.SHARKadmController()

        self._create_transformers()
        self._create_validators_after()

        self._unrestricted_packages = restrict.get_unrestricted_packages()

    def _package_is_unrestricted(self, name: str) -> bool:
        name_no_date = utils.get_zip_name_without_date(name)
        for pack in self._unrestricted_packages:
            if pack.upper() == name_no_date.upper():
                return True
        return False

    @property
    def restrict_data(self):
        if self._restrict_data is None:
            return restrict.RESTRICT_DATA
        return self._restrict_data

    @property
    def zip_archive_paths(self):
        return sorted(self._updated_zip_archive_paths) or sorted(self._zip_archive_paths)

    def _package_is_ok_to_publish(self, data_holder) -> bool:
        if not self.restrict_data:
            return True
        if data_holder.data_type not in restrict.SKIP_DATA_TYPES:
            return True
        if self._package_is_unrestricted(data_holder.zip_archive_path.name):
            return True
        adm_logger.log_workflow(
            f'Not allowed to publish package of data type {data_holder.data_type}: {data_holder.zip_archive_path.name}',
            level=adm_logger.INFO)
        return False

    def _restrict_data_holder(self, data_holder) -> None:
        if not self.restrict_data:
            return
        if self._package_is_unrestricted(data_holder.zip_archive_path.name):
            return
        data_holder.remove_processed_data_directory()
        data_holder.remove_received_data_directory()
        data_holder.remove_readme_files()
        files_left = data_holder.list_files()
        if len(files_left) != 3:
            adm_logger.log_workflow(f'More than 3 expected files left in the restricted zip package: {sorted(files_left)}', level=adm_logger.WARNING)

    def update_zip_archives(self) -> dict:
        publish_not_allowed = []
        self._updated_zip_archive_paths = []
        self._publish_not_allowed_packs = []
        for path in self._zip_archive_paths:
            data_holder = get_zip_archive_data_holder(path)
            if not self._package_is_ok_to_publish(data_holder):
                publish_not_allowed.append(f'{path.name} (data type {data_holder.data_type} not allowed)')
                self._publish_not_allowed_packs.append(path.name)
            self._controller.set_data_holder(data_holder)
            self._run_transformers()
            self._run_validators_after()
            encoding = 'cp1252'
            exporter = exporters.SHARKdataTxtAsGiven(encoding=encoding,
                                                     export_directory=data_holder.unzipped_archive_directory,
                                                     export_file_name=data_holder.unzipped_archive_directory / 'shark_data.txt',
                                                     exclude_columns=[
                                                         'sample_sweref99tm_x',
                                                         'sample_sweref99tm_y',
                                                         'location_wb',
                                                         'location_county',
                                                     ])
            adm_logger.log_workflow(f'Encoding is {encoding} for package {path}', level=adm_logger.DEBUG)

            self._controller.export(exporter)
            self._restrict_data_holder(data_holder)
            rezipped_archive_path = self._zip_directory(data_holder.unzipped_archive_directory)
            self._updated_zip_archive_paths.append(pathlib.Path(rezipped_archive_path))

        return dict(
            publish_not_allowed=publish_not_allowed,
            )

    def publish_is_allowed(self, pack_name: str, allow_all: bool = False) -> bool:
        if allow_all:
            return True
        if not self.restrict_data:
            return True
        if pack_name in self._publish_not_allowed_packs:
            return False
        return True

    def copy_archives_to_sharkdata(self, allow_all: bool = False):
        for source_path in self.zip_archive_paths:
            if not self.publish_is_allowed(source_path.name, allow_all=allow_all):
                continue
            self._copy_archive_to_sharkdata(source_path)
            self._copy_archive_to_zip_directory(source_path)
        # self._copy_archives_to_sharkdata()
        # self._copy_archives_to_zip_directory()

    def _copy_archive_to_sharkdata(self, source_path: pathlib.Path):
        target_root = pathlib.Path(self._config['sharkdata_dataset_directory'])
        target_path = target_root / source_path.name
        shutil.copy2(source_path, target_path)

    def _copy_archive_to_zip_directory(self, source_path: pathlib.Path):
        if not self._config['zip_directory']:
            adm_logger.log_workflow(f'No zip_directory given. Could not copy "locally"!')
            return
        target_root = pathlib.Path(self._config['zip_directory'])
        if not target_root.exists():
            adm_logger.log_workflow(f'Invalid zip_directory: {target_root}')
            return

        current_mapped_zips = utils.get_zip_name_path_mapping(target_root)
        zip_to_remove = None

        source_name_no_date = utils.get_zip_name_without_date(source_path.stem)
        current_zip = current_mapped_zips.get(source_name_no_date)
        if current_zip:
            zip_to_remove = current_zip
        target_path = target_root / source_path.name

        # Remove old zips
        if zip_to_remove:
            adm_logger.log_workflow(f'Removing old package: {zip_to_remove}')
            os.remove(zip_to_remove)

        # Copy new zips
        shutil.copy2(source_path, target_path)

    # def _copy_archives_to_sharkdata(self):
    #     target_root = pathlib.Path(self._config['sharkdata_dataset_directory'])
    #     for source_path in self.zip_archive_paths:
    #         if self.restrict_data and source_path.name in self._publish_not_allowed_packs:
    #             continue
    #         target_path = target_root / source_path.name
    #         shutil.copy2(source_path, target_path)
    #
    # def _copy_archives_to_zip_directory(self):
    #     if not self._config['zip_directory']:
    #         adm_logger.log_workflow(f'No zip_directory given. Could not copy "locally"!')
    #         return
    #     target_root = pathlib.Path(self._config['zip_directory'])
    #     if not target_root.exists():
    #         adm_logger.log_workflow(f'Invalid zip_directory: {target_root}')
    #         return
    #
    #     current_mapped_zips = utils.get_zip_name_path_mapping(target_root)
    #     zips_to_remove = []
    #     zips_to_copy = []
    #     for source_path in self.zip_archive_paths:
    #         if self.restrict_data and source_path.name in self._publish_not_allowed_packs:
    #             continue
    #         source_name_no_date = utils.get_zip_name_without_date(source_path.stem)
    #         current_zip = current_mapped_zips.get(source_name_no_date)
    #         if current_zip:
    #             zips_to_remove.append(current_zip)
    #         target_path = target_root / source_path.name
    #         zips_to_copy.append((source_path, target_path))
    #
    #     # Remove old zips
    #     for path in zips_to_remove:
    #         adm_logger.log_workflow(f'Removing old package: {path}')
    #         os.remove(path)
    #
    #     # Copy new zips
    #     for source_path, target_path in zips_to_copy:
    #         shutil.copy2(source_path, target_path)

    @property
    def all_transformers(self) -> dict[str, list[transformers.Transformer]]:
        return dict(
            mandatory=self._transformers,
            restricted=self._restricted_transformers
        )

    @property
    def validators_after(self) -> list[validators.Validator]:
        return self._validators_after

    @property
    def sharkdata_dataset_directory(self) -> str:
        return self._config['sharkdata_dataset_directory']

    def _create_validators_after(self) -> None:
        self._validators_after = []

        if not self.restrict_data:
            return
        self._validators_after.append(
            validators.AssertMinMaxDepthCombination(
                valid_data_types=['Chlorophyll'],
                valid_combinations=[
                    '0-5',
                    '0-10',
                    '0-14',
                    '0-20',
                    '10-20',
                    '0-999',
                    '999-999',
                ],
            )
        )

        self._validators_after.append(
            validators.AssertMinMaxDepthCombination(
                valid_data_types=['Phytoplankton'],
                valid_combinations=[
                    '0-0',
                    '0-5',
                    '0-10',
                    '0-14',
                    '0-20',
                    '10-20',
                    '0-999',
                    '999-999',
                ],
            )
        )

        self._validators_after.append(
            validators.AssertMinMaxDepthCombination(
                valid_data_types=['Zooplankton'],
                valid_combinations=[
                    '0-25',
                    '0-30',
                    '30-60',
                    '0-35',
                    '0-999',
                    '999-999',
                ],
            )
        )

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

        self._restricted_transformers = []
        if self.restrict_data:
            dfilter = data_filter.DataFilterRestrictDepth()
            # self._restricted_transformers.append(transformers.AddSamplePositionDD())
            self._restricted_transformers.append(transformers.AddSamplePositionSweref99tm())
            self._restricted_transformers.append(transformers.AddLocationWB())
            self._restricted_transformers.append(transformers.AddLocationCounty())
            self._restricted_transformers.extend([
                transformers.RemoveValuesInColumns(*restrict.DEPTH_COLUMNS, replace_value=restrict.DEPTH_REPLACE_VALUE, data_filter=dfilter),
                transformers.RemoveValuesInColumns(*restrict.SECCHI_COLUMNS, replace_value=restrict.SECCHI_REPLACE_VALUE, data_filter=dfilter),
                transformers.RemoveValuesInColumns(*restrict.COMMENT_COLUMNS, replace_value=restrict.COMMENT_REPLACE_VALUE, data_filter=dfilter),

                transformers.RemoveRowsForParameters(*restrict.REMOVE_PARAMETER_ROWS, data_filter=dfilter),

                transformers.RemoveRowsAtDepthRestriction(
                    valid_data_types=[
                        'epibenthos',
                        'epibenthos_dropvideo',
                        'zoobenthos',
                    ],
                    data_filter=dfilter
                ),

                transformers.RemoveDeepestDepthAtEachVisit(
                    valid_data_types=['PhysicalChemical'],
                    depth_column='sample_depth_m',
                    also_remove_from_columns=['sample_id', 'shark_sample_id'],
                    replace_value=restrict.DEPTH_REPLACE_VALUE,
                    keep_single_depth_at_surface=True,
                    data_filter=dfilter,
                ),
            ])
            for col in ['sample_depth_m', 'sample_min_depth_m', 'sample_max_depth_m']:
                self._restricted_transformers.append(transformers.RemoveDeepestDepthAtEachVisit(
                    valid_data_types=['Bacterioplankton', 'Harbourporpoise'],
                    depth_column=col,
                    also_remove_from_columns=['sample_id', 'shark_sample_id', 'shark_sample_id_md5'],
                    replace_value=restrict.DEPTH_REPLACE_VALUE,
                    data_filter=dfilter,
                ))

            self._restricted_transformers.append(transformers.RemoveInterval(
                valid_data_types=['Chlorophyll'],
                keep_intervals=[
                    '0-5',
                    '0-10',
                    '0-14',
                    '0-20',
                    '10-20',
                ],
                keep_if_min_depths_are=['0'],
                replace_value=restrict.DEPTH_REPLACE_VALUE,
                also_remove_from_columns=['sample_id', 'shark_sample_id', 'shark_sample_id_md5'],
                data_filter=dfilter,
            ))

            self._restricted_transformers.append(transformers.RemoveInterval(
                valid_data_types=['Phytoplankton'],
                keep_intervals=[
                    '0-0'
                    '0-5',
                    '0-10',
                    '0-14',
                    '0-20',
                    '10-20',
                ],
                keep_if_min_depths_are=['0'],
                replace_value=restrict.DEPTH_REPLACE_VALUE,
                also_remove_from_columns=['sample_id', 'shark_sample_id', 'shark_sample_id_md5'],
                data_filter=dfilter,
            ))

            self._restricted_transformers.append(transformers.RemoveInterval(
                valid_data_types=['Zooplankton'],
                keep_intervals=[
                    '0-25',
                    '0-30',
                    '30-60',
                    '0-35',
                ],
                keep_if_min_depths_are=['0'],
                replace_value=restrict.DEPTH_REPLACE_VALUE,
                also_replace_in_columns=['sampled_volume_l', 'flowmeter_length_m'],
                also_remove_from_columns=['sample_id', 'shark_sample_id_md5'],
                data_filter=dfilter,
            ))

    def _run_transformers(self) -> None:
        for trans in self._transformers:
            self._controller.transform(trans)
        if not self.restrict_data:
            return
        if self._package_is_unrestricted(self._controller.dataset_name):
            return
        for trans in self._restricted_transformers:
            print(f'{trans=}')
            self._controller.transform(trans)

    def _run_validators_after(self) -> None:
        for val in self._validators_after:
            self._controller.validate(val)

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
