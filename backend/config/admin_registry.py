"""
Registers an app's models in Django admin so every table can be browsed at
/admin/. Models that already have a hand-written ModelAdmin are left alone.

Usage, in an app's admin.py::

    from config.admin_registry import register_app_models
    register_app_models("doctors")
"""

from django.apps import apps
from django.contrib import admin
from django.db import models

MAX_LIST_COLUMNS = 7
MAX_SEARCH_FIELDS = 4
SEARCHABLE = (models.CharField, models.EmailField)
SKIP_IN_LIST = (models.TextField, models.JSONField, models.BinaryField, models.FileField)


def _list_columns(model):
    columns = [f.name for f in model._meta.concrete_fields if not isinstance(f, SKIP_IN_LIST)]
    return tuple(columns[:MAX_LIST_COLUMNS])


def _search_fields(model):
    fields = [f.name for f in model._meta.concrete_fields if isinstance(f, SEARCHABLE) and not f.choices]
    return tuple(fields[:MAX_SEARCH_FIELDS])


class ReadOnlyAdminMixin:
    """For append-only records such as audit logs: view, never add/change/delete."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def admin_class_for(model, read_only=False):
    attrs = {
        "list_display": _list_columns(model),
        "search_fields": _search_fields(model),
        "ordering": ("-pk",),
        "list_per_page": 50,
        # Foreign keys as plain ids: no dropdown that loads a whole table.
        "raw_id_fields": tuple(
            f.name for f in model._meta.concrete_fields if isinstance(f, models.ForeignKey)
        ),
    }
    bases = (ReadOnlyAdminMixin, admin.ModelAdmin) if read_only else (admin.ModelAdmin,)
    return type(f"{model.__name__}Admin", bases, attrs)


def register_app_models(app_label, read_only=False):
    """Register every model of ``app_label`` that admin does not know yet."""
    for model in apps.get_app_config(app_label).get_models():
        if not admin.site.is_registered(model):
            admin.site.register(model, admin_class_for(model, read_only=read_only))
