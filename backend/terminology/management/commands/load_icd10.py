"""
Load ICD-10 codes into terminology.ICD10Code.

    manage.py load_icd10                       # bundled list of common codes
    manage.py load_icd10 icd10cm_order_2026.txt  # full CMS ICD-10-CM release

Accepted files:
- CSV with a header row: ``code,description[,billable]``
- CMS ICD-10-CM "order" file (fixed width, from the public-domain release at
  https://www.cms.gov/medicare/coding-billing/icd-10-codes)
- CMS ICD-10-CM "codes" file (``CODE  Description`` per line)

Re-running updates descriptions in place; ``--replace`` also removes codes
missing from the file; ``--if-empty`` loads only into an empty table (used at
container start so a full CMS load is never overwritten).
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from terminology.models import ICD10Code, compact_code, display_code

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "icd10_common.csv"
BATCH_SIZE = 2000


def _truthy(value):
    return str(value).strip().lower() not in ("0", "false", "no", "n")


def _read_csv(handle):
    reader = csv.DictReader(handle)
    if not reader.fieldnames or not {"code", "description"} <= set(reader.fieldnames):
        raise CommandError("CSV needs a header row with 'code' and 'description' columns.")
    for row in reader:
        yield row["code"], row["description"], _truthy(row.get("billable", "1"))


def _is_order_line(line):
    return len(line) > 16 and line[:5].strip().isdigit() and line[14] in "01"


def _read_cms(handle):
    for line in handle:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        if _is_order_line(line):
            # order(5) code(7) billable(1) short(60) long
            long_desc = line[77:].strip() or line[16:76].strip()
            yield line[6:13], long_desc, line[14] == "1"
        else:
            code, _, description = line.strip().partition(" ")
            yield code, description.strip(), True


def read_codes(path):
    """(code, description, billable) rows from ``path``; invalid rows skipped."""
    with open(path, encoding="utf-8-sig") as handle:
        rows = _read_csv(handle) if path.suffix.lower() == ".csv" else _read_cms(handle)
        for code, description, billable in rows:
            compact = compact_code(code)
            description = " ".join(str(description or "").split())[:300]
            if 3 <= len(compact) <= 7 and compact[0].isalpha() and description:
                yield compact, description, billable


class Command(BaseCommand):
    help = "Load ICD-10 codes from a CSV or CMS ICD-10-CM file (default: bundled common codes)."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(DEFAULT_FILE))
        parser.add_argument("--replace", action="store_true", help="Delete codes that are not in the file.")
        parser.add_argument("--if-empty", action="store_true", help="Do nothing when codes are already loaded.")

    def handle(self, *args, path, replace, if_empty, **options):
        if if_empty and ICD10Code.objects.exists():
            self.stdout.write("ICD-10 codes already loaded; nothing to do.")
            return
        path = Path(path)
        if not path.is_file():
            raise CommandError(f"File not found: {path}")
        incoming = {compact: (description, billable) for compact, description, billable in read_codes(path)}
        if not incoming:
            raise CommandError("No valid ICD-10 rows found in the file.")
        created, updated = self._upsert(incoming)
        removed = 0
        if replace:
            removed, _ = ICD10Code.objects.exclude(code_compact__in=list(incoming)).delete()
        self.stdout.write(self.style.SUCCESS(
            f"ICD-10: {created} added, {updated} updated, {removed} removed ({len(incoming)} in file)."
        ))

    @transaction.atomic
    def _upsert(self, incoming):
        existing = {row.code_compact: row for row in ICD10Code.objects.all()}
        new_rows, changed = [], []
        for compact, (description, billable) in incoming.items():
            row = existing.get(compact)
            if row is None:
                new_rows.append(ICD10Code(
                    code=display_code(compact), code_compact=compact, description=description,
                    search_text=description.lower(), billable=billable,
                ))
            elif (row.description, row.billable) != (description, billable):
                row.description, row.search_text, row.billable = description, description.lower(), billable
                changed.append(row)
        ICD10Code.objects.bulk_create(new_rows, batch_size=BATCH_SIZE)
        ICD10Code.objects.bulk_update(changed, ["description", "search_text", "billable"], batch_size=BATCH_SIZE)
        return len(new_rows), len(changed)
