"""
BUG-02 repair: close queue tokens left open by visits that are already over.

Before the visit lifecycle fix, completing a visit from the Consultation screen
never touched its token, so tokens stayed Waiting or In Consultation after the
visit was Completed (or Cancelled). New changes keep them in step; this closes
the ones written before. A token of a Completed visit is completed and one of a
Cancelled visit is cancelled, with its appointment kept in step.

Dry run by default; prints counts and token ids only, never patient names.

    python manage.py close_stale_queue_tokens                 # report
    python manage.py close_stale_queue_tokens --apply         # close them
    python manage.py close_stale_queue_tokens --apply --hospital 3
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from encounters.services.visit_lifecycle import close_token_of_closed_visit, stale_tokens


class Command(BaseCommand):
    help = "Close queue tokens whose visit is already Completed or Cancelled (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Close the tokens (otherwise only report).")
        parser.add_argument("--hospital", type=int, help="Only this hospital id.")

    def handle(self, *args, **options):
        hospital_id = options.get("hospital")
        ids = list(stale_tokens(hospital_id).values_list("pk", flat=True))
        self.stdout.write(f"Open tokens of closed visits: {len(ids)}")
        if ids:
            self.stdout.write("Token ids: " + ", ".join(str(pk) for pk in ids))
        misplaced = list(stale_tokens(hospital_id, first_of_visit=False).values_list("pk", flat=True))
        if misplaced:
            self.stdout.write(
                f"Tokens put on another appointment's closed visit (not closed; cancel or reissue them): "
                f"{len(misplaced)}. Token ids: " + ", ".join(str(pk) for pk in misplaced)
            )
        if not options["apply"]:
            self.stdout.write("Dry run: nothing changed. Run again with --apply to close them.")
            return
        closed = 0
        for pk in ids:
            with transaction.atomic():
                if close_token_of_closed_visit(pk) is not None:
                    closed += 1
        still_open = stale_tokens(hospital_id).count()
        self.stdout.write(f"Closed: {closed}. Still open: {still_open}.")
        if still_open:
            self.stderr.write("Some tokens changed while this ran; run it again to check.")
