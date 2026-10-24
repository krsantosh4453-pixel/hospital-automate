"""Generic synthetic-record factory used by the tenant-isolation probes.

Fills every required field with a synthetic value so a record can be created
for any model without hand-writing fixtures. Only synthetic data is produced.
"""

import datetime
import itertools
from decimal import Decimal

from django.db import models
from django.utils import timezone

_counter = itertools.count(1)


class SyntheticFactory:
    def __init__(self, fixed=None):
        # fixed: {model_label: instance} used for FK targets (e.g. the tenant)
        self.fixed = dict(fixed or {})
        self.made = {}

    def value_for(self, field):
        n = next(_counter)
        if field.choices:
            return field.choices[0][0]
        if isinstance(field, models.EmailField):
            return f"synthetic{n}@example.test"
        if isinstance(field, (models.CharField, models.TextField, models.SlugField)):
            max_len = getattr(field, "max_length", None) or 20
            return f"S{n}"[:max_len]
        if isinstance(field, models.BooleanField):
            return False
        if isinstance(field, models.DecimalField):
            return Decimal("1.00")
        if isinstance(field, (models.IntegerField, models.FloatField)):
            return 1
        if isinstance(field, models.DateTimeField):
            return timezone.now()
        if isinstance(field, models.DateField):
            return datetime.date.today()
        if isinstance(field, models.TimeField):
            return datetime.time(10, 0)
        if isinstance(field, models.JSONField):
            return {}
        if isinstance(field, models.UUIDField):
            import uuid
            return uuid.uuid4()
        if isinstance(field, models.GenericIPAddressField):
            return "127.0.0.1"
        if isinstance(field, models.FileField):
            return "synthetic/test.txt"
        return None

    def get(self, model):
        label = model._meta.label
        if label in self.fixed:
            return self.fixed[label]
        if label not in self.made:
            self.made[label] = self.make(model)
        return self.made[label]

    def make(self, model, **overrides):
        kwargs = {}
        for field in model._meta.concrete_fields:
            if field.name in overrides or field.primary_key:
                continue
            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                target = field.related_model
                if target._meta.label in self.fixed:
                    kwargs[field.name] = self.fixed[target._meta.label]
                elif not field.null:
                    if isinstance(field, models.OneToOneField):
                        kwargs[field.name] = self.make(target)
                    else:
                        kwargs[field.name] = self.get(target)
                continue
            if field.has_default() or field.null or field.blank and not isinstance(
                field, (models.DateField, models.DecimalField, models.IntegerField, models.FloatField)
            ):
                continue
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue
            kwargs[field.name] = self.value_for(field)
        kwargs.update(overrides)
        obj = model(**kwargs)
        # Bypass model.save() side effects that need extra context only if needed.
        obj.save()
        return obj
