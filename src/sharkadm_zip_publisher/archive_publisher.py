import os
import pathlib
import shutil
from typing import Dict, List

from sharkadm import transformers, controller, exporters, adm_logger, validators, \
    multi_transformers
from sharkadm import utils as sharkadm_utils
from sharkadm.data import get_zip_archive_data_holder, get_polars_zip_archive_data_holder
from sharkadm.transformers import PolarsTransformer
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
        self._transformers: list[transformers.PolarsTransformer] = []
        self._restricted_transformers: list[transformers.PolarsTransformer] = []
        self._cleanup_transformers: list[transformers.PolarsTransformer] = []
        self._validators_after: list[validators.Validator] = []
        self._updated_zip_archive_paths: list[pathlib.Path] = []
        self._publish_not_allowed_packs: list[pathlib.Path] = []

        self._restrict_data = restrict_data

        # Filters
        self._main_filter = data_filter.PolarsDataFilterRestrictAreaRredorO()
        # self._main_filter = data_filter.PolarsDataFilterRestrictAreaGandC()
        self._r_filter = data_filter.PolarsDataFilterRestrictAreaRred()
        self._par_cover_filter = data_filter.PolarsDataFilterMatchInColumn(
            column='scientific_name',
            pattern="^COVER.*$")
        self._rep_par_cover_filter = data_filter.PolarsDataFilterMatchInColumn(
            column='reported_scientific_name',
            pattern="^COVER.*$")
        self._secchi_qf_filter = (data_filter.PolarsDataFilterMatchInColumn(
            column='quality_flag',
            pattern=".+") & data_filter.PolarsDataFilterMatchInColumn(
                column="parameter",
                pattern="Secchi depth"
        ))

        # self._controller = controller.SHARKadmController()
        self._controller = controller.SHARKadmPolarsController()

        self._create_transformers()
        # self._create_validators_after()

        self._unrestricted_packages = restrict.get_unrestricted_packages()

    def _package_is_unrestricted(self, name: str) -> bool:
        return False
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
        if restrict.ONLY_PUBLISH_DATA_TYPES and data_holder.data_type_internal not in restrict.ONLY_PUBLISH_DATA_TYPES:
            return False
        if data_holder.data_type_internal not in restrict.DONT_PUBLISH_DATA_TYPES:
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
        if self._controller.data_holder.data_type_internal in restrict.UNRESTRICTED_DATA_TYPES:
            return
        if self._package_is_unrestricted(data_holder.zip_archive_path.name):
            return
        if data_holder.data_type_internal in restrict.DONT_REMOVE_FOLDERS_FOR_DATA_TYPES:
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
            # data_holder = get_zip_archive_data_holder(path)
            data_holder = get_polars_zip_archive_data_holder(path)
            if not self._package_is_ok_to_publish(data_holder):
                publish_not_allowed.append(f'{path.name} (data type {data_holder.data_type} not allowed)')
                self._publish_not_allowed_packs.append(path.name)
                continue
            self._controller.set_data_holder(data_holder)
            len_data_before = len(self._controller.data)
            # print(f"A {[col for col in self._controller.data_holder.data.columns if 'location' in col]}")
            self._run_transformers()
            # print(f"B {[col for col in self._controller.data_holder.data.columns if 'location' in col]}")
            mask = self._main_filter.get_filter_mask(self._controller.data_holder)
            filt_df = self._controller.data.filter(~mask)
            len_filt_data = len(filt_df)
            self._run_cleanup_transformers()

            if len_filt_data != len_data_before:
                self._run_validators_after()
                # if not len(self._controller.data):
                #     adm_logger.log_workflow(f'Skipping empty package: {self._controller.dataset_name}', level=adm_logger.WARNING)
                #     continue
                encoding = 'cp1252'
                exporter = exporters.SHARKdataTxtAsGiven(encoding=encoding,
                                                         export_directory=data_holder.unzipped_archive_directory,
                                                         export_file_name=data_holder.unzipped_archive_directory / 'shark_data.txt',
                                                         exclude_columns=(
                                                             # 'sample_sweref99tm_x',
                                                             # 'sample_sweref99tm_y',
                                                             # 'location_wb',
                                                             # 'location_county',
                                                         ))
                adm_logger.log_workflow(f'Encoding is {encoding} for package {path}', level=adm_logger.DEBUG)

                self._controller.transform(transformers.ConvertFromPolarsToPandas())
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

    @property
    def all_transformers(self) -> dict[str, list[PolarsTransformer]]:
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

    def _create_transformers(self):
        self._transformers = [
            ]

        self._cleanup_transformers = [
            transformers.PolarsRemoveColumns(
                "row_number",
                "location_ra",
                "location_rb",
                "location_rc",
                "location_rg",
                "location_rh",
                "location_ro",
                "location_r",
                "location_wb",
                "location_county",
                "approved_key",
                "sample_sweref99tm_x",
                "sample_sweref99tm_y",
                "reported_visit_date",
                "reported_sample_date",
            ),
            transformers.PolarsRemoveColumns(
                "sample_project_name_sv",
                "sample_orderer_name_sv",
                "sampling_laboratory_name_sv",
                "analytical_laboratory_name_sv",
                "reporting_institute_name_sv",
            ),
            transformers.PolarsRemoveColumns(
                "approved_key",
            )


        ]

        self._restricted_transformers = []
        if self.restrict_data:

            self._restricted_transformers.extend([

                transformers.PolarsAddSamplePositionSweref99tm(),
                # transformers.PolarsAddLocationRA(),
                # transformers.PolarsAddLocationRB(),
                transformers.PolarsAddLocationRC(),
                transformers.PolarsAddLocationRG(),
                # transformers.PolarsAddLocationRH(),
                transformers.PolarsAddLocationRO(),
                # transformers.PolarsAddLocationR(),

                transformers.PolarsRemoveProfiles(data_filter=self._main_filter),  # has to be before RemoveMask

                transformers.PolarsRemoveValueInColumns(
                    *restrict.REMOVE_VALUES_FOR_COLUMNS,
                    replace_value=restrict.REPLACE_COLUMN_VALUE,
                    data_filter=self._main_filter),

                transformers.PolarsRemoveValueInColumns(
                    *restrict.COMMENT_COLUMNS,
                    replace_value=restrict.REPLACE_COMMENT_VALUE,
                    data_filter=self._main_filter),

                transformers.PolarsRemoveValueInRowsForParameters(
                    *restrict.REMOVE_VALUES_FOR_PARAMETERS,
                    replace_value=restrict.REPLACE_PARAMETER_VALUE,
                    data_filter=self._main_filter),

                transformers.PolarsReplaceColumnWithMask(
                    valid_data_types=("epibenthos",),
                    column="scientific_name",
                    replace_value=restrict.REPLACE_SCIENTIFIC_NAME_VALUE,
                    data_filter=self._main_filter & self._par_cover_filter),

                transformers.PolarsReplaceColumnWithMask(
                    valid_data_types=("epibenthos",),
                    column="reported_scientific_name",
                    replace_value=restrict.REPLACE_SCIENTIFIC_NAME_VALUE,
                    data_filter=self._main_filter & self._rep_par_cover_filter),

                transformers.PolarsReplaceColumnWithMask(
                    valid_data_types=("physicalchemical",),
                    column="quality_flag",
                    replace_value=restrict.REPLACE_SECCHI_VALUE,
                    data_filter=self._main_filter & self._secchi_qf_filter),

                # No ox
                transformers.PolarsRemoveValueInColumns(
                    *restrict.ALL_BUT_OX,
                    replace_value=restrict.REPLACE_COLUMN_VALUE,
                    data_filter=self._r_filter),
            ])

    def _run_transformers(self) -> None:
        for trans in self._transformers:
            self._controller.transform(trans)
        if not self.restrict_data:
            return
        if self._controller.data_holder.data_type_internal in restrict.UNRESTRICTED_DATA_TYPES:
            return
        if self._package_is_unrestricted(self._controller.dataset_name):
            return
        for trans in self._restricted_transformers:
            self._controller.transform(trans)

    def _run_cleanup_transformers(self):
        for trans in self._cleanup_transformers:
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
