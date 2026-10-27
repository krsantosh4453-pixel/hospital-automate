"""
Django settings package for Hospital Management System.

This package provides environment-specific settings:
- base.py: Common settings shared across all environments
- development.py: Development settings (DEBUG=True, SQLite, verbose logging)
- production.py: Production settings (hardened, PostgreSQL, Redis, structured logging)
- testing.py: Test settings (in-memory DB, fast password hashing, disabled external services)

The appropriate settings module is selected via the DJANGO_SETTINGS_MODULE environment variable:
- development: config.settings.development
- production: config.settings.production
- testing: config.settings.testing

Default is development for local development.
"""

import os

# Determine environment
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development').lower()

# Python runs this file before any submodule, so importing
# config.settings.testing or config.settings.production would otherwise also
# execute development.py and require its variables. Select an environment
# only when this package itself is the settings module.
if os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings') == 'config.settings':
    if ENVIRONMENT == 'production':
        from .production import *  # noqa: F403,F401
    elif ENVIRONMENT == 'testing':
        from .testing import *  # noqa: F403,F401
    else:
        from .development import *  # noqa: F403,F401

# Export the environment for use in other modules
__all__ = ['ENVIRONMENT']