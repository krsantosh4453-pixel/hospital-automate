"""
Background scribe steps. The API claims the transcript or draft first, then
queues the task, so a client can poll instead of waiting on the provider.
"""

from celery import shared_task


@shared_task(ignore_result=True, acks_late=True)
def transcribe_consultation(transcript_id):
    from .services.pipeline import run_transcription

    run_transcription(transcript_id)


@shared_task(ignore_result=True, acks_late=True)
def generate_draft(draft_id):
    from .services.pipeline import run_generation

    run_generation(draft_id)
