from django.db.models.signals import post_save
from django.dispatch import receiver

from reports.models import ReportTemplate, SavedReport, ScheduledReport


@receiver(post_save, sender=ReportTemplate)
def create_system_templates(sender, instance, created, **kwargs):
    """Create default system report templates on first run."""
    if created and instance.is_system:
        pass


@receiver(post_save, sender=SavedReport)
def saved_report_created(sender, instance, created, **kwargs):
    """Log when a report is saved."""
    pass


@receiver(post_save, sender=ScheduledReport)
def scheduled_report_created(sender, instance, created, **kwargs):
    """Log when a scheduled report is created."""
    pass