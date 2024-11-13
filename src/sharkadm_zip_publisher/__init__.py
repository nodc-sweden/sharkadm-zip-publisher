from sharkadm_zip_publisher.flet_app import run_app

from sharkadm import adm_logger

try:
    from nodc_codes import update_config_files
    update_config_files()
    adm_logger.log_workflow(f'nodc_codes config files updated successfully.', level=adm_logger.INFO)
except Exception as e:
    adm_logger.log_workflow(f'Could not update nodc_codes config files', level=adm_logger.WARNING)
