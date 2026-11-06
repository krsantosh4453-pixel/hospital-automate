"""
Reference code systems. ICD-10 codes are loaded with
``manage.py load_icd10`` and are the same for every hospital.
"""

from django.db import models


def compact_code(code):
    """ICD-10 code without the dot, upper case: ``e11.9`` -> ``E119``."""
    return "".join(ch for ch in str(code or "") if ch.isalnum()).upper()


def display_code(code):
    """ICD-10 code with the dot after the category: ``E119`` -> ``E11.9``."""
    compact = compact_code(code)
    return f"{compact[:3]}.{compact[3:]}" if len(compact) > 3 else compact


class ICD10Code(models.Model):
    code = models.CharField(max_length=10, unique=True)  # display form, e.g. E11.9
    code_compact = models.CharField(max_length=10, db_index=True)  # E119, for prefix search
    description = models.CharField(max_length=300)
    # Lower-case description, matched by the search endpoint.
    search_text = models.CharField(max_length=300, db_index=True)
    # False for category headers that are not valid billable codes.
    billable = models.BooleanField(default=True)

    class Meta:
        ordering = ["code_compact"]
        verbose_name = "ICD-10 code"

    def __str__(self):
        return f"{self.code} {self.description}"
