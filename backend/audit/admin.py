from config.admin_registry import register_app_models

# Audit records are append-only: view them, never edit.
register_app_models("audit", read_only=True)
