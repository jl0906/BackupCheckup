"""Constants for BackupCheckup."""

from homeassistant.const import Platform

DOMAIN = "backup_checkup"
NAME = "BackupCheckup"
VERSION = "1.1.0"

PLATFORMS: tuple[Platform, ...] = (Platform.SENSOR, Platform.BINARY_SENSOR)

CONF_MAX_AGE_DAYS = "max_age_days"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"

DEFAULT_MAX_AGE_DAYS = 4
DEFAULT_UPDATE_INTERVAL_MINUTES = 1
MIN_MAX_AGE_DAYS = 1
MAX_MAX_AGE_DAYS = 365
MIN_UPDATE_INTERVAL_MINUTES = 1
MAX_UPDATE_INTERVAL_MINUTES = 60

STATUS_OK = "ok"
STATUS_NO_BACKUPS = "no_backups"
STATUS_AUTOMATIC_BACKUP_OVERDUE = "automatic_backup_overdue"
STATUS_BACKUP_STALE = "backup_stale"
STATUS_AUTOMATIC_BACKUP_FAILED = "automatic_backup_failed"
STATUS_SCHEDULE_MISSING = "schedule_missing"
STATUS_SCHEDULE_OVERDUE = "schedule_overdue"
STATUS_MANAGER_UNAVAILABLE = "manager_unavailable"
STATUS_STORAGE_ERROR = "storage_error"

STATUS_OPTIONS = [
    STATUS_OK,
    STATUS_NO_BACKUPS,
    STATUS_AUTOMATIC_BACKUP_OVERDUE,
    STATUS_BACKUP_STALE,
    STATUS_AUTOMATIC_BACKUP_FAILED,
    STATUS_SCHEDULE_MISSING,
    STATUS_SCHEDULE_OVERDUE,
    STATUS_MANAGER_UNAVAILABLE,
    STATUS_STORAGE_ERROR,
]

CORE_BACKUP_MANAGER_STATE = "sensor.backup_backup_manager_state"
CORE_LAST_AUTOMATIC_ATTEMPT = "sensor.backup_last_attempted_automatic_backup"
CORE_LAST_SUCCESSFUL_AUTOMATIC_BACKUP = "sensor.backup_last_successful_automatic_backup"
CORE_NEXT_AUTOMATIC_BACKUP = "sensor.backup_next_scheduled_automatic_backup"
