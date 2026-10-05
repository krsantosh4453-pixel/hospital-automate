"""
Queue Prediction Service

Provides baseline wait-time estimation for queue tokens.
Designed for future ML model extensibility via the PredictionProvider pattern.

Architecture:
    QueuePredictionService
        └── PredictionProvider (protocol)
            ├── BaselineEstimator (current)
            └── MLModelEstimator (future)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from django.db.models import Avg, Count, F
from django.utils import timezone

from encounters.models import QueueToken


@dataclass
class QueueEstimate:
    """
    Result of a queue wait-time estimation.

    Attributes:
        queue_position: 1-based position in the waiting queue.
        estimated_wait_minutes: Predicted minutes until consultation starts.
        estimated_start_time: Predicted consultation start timestamp.
        last_updated: When this estimate was calculated.
        confidence: Optional confidence score (0.0-1.0) for the estimate.
        method: Estimation method used (e.g., "baseline", "ml").
    """
    queue_position: int
    estimated_wait_minutes: int
    estimated_start_time: datetime
    last_updated: datetime
    confidence: Optional[float] = None
    method: str = "baseline"


class PredictionProvider(ABC):
    """
    Abstract interface for wait-time estimation providers.

    Implementations can range from simple heuristics to trained ML models.
    The QueuePredictionService delegates to the active provider.
    """

    @abstractmethod
    def estimate(
        self,
        *,
        hospital_id: int,
        doctor_id: int,
        token_date: datetime.date,
        current_token_number: int,
        token_created_at: datetime,
    ) -> QueueEstimate:
        """
        Calculate wait-time estimate for a token.

        Args:
            hospital_id: Hospital scope.
            doctor_id: Doctor scope.
            token_date: Calendar day of the token.
            current_token_number: The token's assigned number.
            token_created_at: When the token was created.

        Returns:
            QueueEstimate with position, wait time, start time, and metadata.
        """
        pass


class BaselineEstimator(PredictionProvider):
    """
    Baseline wait-time estimator using simple queue arithmetic.

    Formula:
        patients_ahead = count of tokens with lower token_number and status in WAITING/CALLED/ACKNOWLEDGED/READY
        avg_service_time = historical average consultation duration for this doctor (fallback 15 min)
        estimated_wait = patients_ahead * avg_service_time
    """

    DEFAULT_AVG_MINUTES = 15
    MIN_CONFIDENCE = 0.3
    MAX_CONFIDENCE = 0.7

    def estimate(
        self,
        *,
        hospital_id: int,
        doctor_id: int,
        token_date,
        current_token_number: int,
        token_created_at: datetime,
    ) -> QueueEstimate:
        from encounters.models import QueueToken

        waiting_statuses = [
            QueueToken.Status.WAITING,
            QueueToken.Status.CALLED,
            QueueToken.Status.ACKNOWLEDGED,
            QueueToken.Status.READY,
        ]

        patients_ahead = QueueToken.objects.filter(
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            token_date=token_date,
            token_number__lt=current_token_number,
            status__in=waiting_statuses,
        ).count()

        avg_minutes = self._get_avg_consultation_duration(doctor_id)
        estimated_wait = patients_ahead * avg_minutes
        estimated_start = timezone.now() + timedelta(minutes=estimated_wait)

        confidence = self._calculate_confidence(patients_ahead, avg_minutes)

        return QueueEstimate(
            queue_position=patients_ahead + 1,
            estimated_wait_minutes=estimated_wait,
            estimated_start_time=estimated_start,
            last_updated=timezone.now(),
            confidence=confidence,
            method="baseline",
        )

    def _get_avg_consultation_duration(self, doctor_id: int) -> int:
        """
        Calculate average consultation duration from completed tokens.

        Looks at tokens that went IN_CONSULTATION → COMPLETED and measures
        the time between consultation_started_at and completed_at.
        """
        from encounters.models import QueueToken

        completed = QueueToken.objects.filter(
            doctor_id=doctor_id,
            status=QueueToken.Status.COMPLETED,
            consultation_started_at__isnull=False,
            completed_at__isnull=False,
        ).annotate(
            duration=F("completed_at") - F("consultation_started_at")
        )

        if not completed.exists():
            return self.DEFAULT_AVG_MINUTES

        avg_seconds = completed.aggregate(
            avg_duration=Avg("duration")
        )["avg_duration"]

        if avg_seconds is None:
            return self.DEFAULT_AVG_MINUTES

        avg_minutes = max(1, int(avg_seconds.total_seconds() // 60))
        return min(avg_minutes, 120)

    def _calculate_confidence(self, patients_ahead: int, avg_minutes: int) -> float:
        """
        Heuristic confidence based on queue depth and data availability.

        - Fewer patients ahead = higher confidence
        - More historical data = higher confidence (not tracked here, using defaults)
        """
        if patients_ahead == 0:
            return self.MAX_CONFIDENCE

        confidence = self.MAX_CONFIDENCE - (patients_ahead * 0.05)
        return max(self.MIN_CONFIDENCE, min(confidence, self.MAX_CONFIDENCE))


class QueuePredictionService:
    """
    High-level service for queue wait-time predictions.

    Encapsulates provider selection and provides a stable API for views/serializers.
    """

    def __init__(self, provider: Optional[PredictionProvider] = None):
        self._provider = provider or BaselineEstimator()

    @property
    def provider(self) -> PredictionProvider:
        return self._provider

    @provider.setter
    def provider(self, value: PredictionProvider):
        if not isinstance(value, PredictionProvider):
            raise TypeError("Provider must implement PredictionProvider")
        self._provider = value

    def estimate_for_token(self, token: QueueToken) -> QueueEstimate:
        """
        Calculate estimate for a specific token.
        """
        return self._provider.estimate(
            hospital_id=token.hospital_id,
            doctor_id=token.doctor_id,
            token_date=token.token_date,
            current_token_number=token.token_number,
            token_created_at=token.created_at,
        )

    def update_token_estimate(self, token: QueueToken) -> QueueToken:
        """
        Update a token's estimation fields and save.

        Returns the updated token.
        """
        estimate = self.estimate_for_token(token)
        token.queue_position = estimate.queue_position
        token.estimated_wait_minutes = estimate.estimated_wait_minutes
        token.estimated_start_time = estimate.estimated_start_time
        token.last_updated = estimate.last_updated
        token.save(
            update_fields=[
                "queue_position",
                "estimated_wait_minutes",
                "estimated_start_time",
                "last_updated",
            ]
        )
        return token

    def recalculate_all_waiting(self, hospital_id: int, doctor_id: int, token_date=None) -> int:
        """
        Recalculate estimates for all waiting tokens for a doctor.

        Returns count of updated tokens.
        """
        token_date = token_date or timezone.localdate()

        waiting_statuses = [
            QueueToken.Status.WAITING,
            QueueToken.Status.CALLED,
            QueueToken.Status.ACKNOWLEDGED,
            QueueToken.Status.READY,
        ]

        tokens = QueueToken.objects.filter(
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            token_date=token_date,
            status__in=waiting_statuses,
        ).order_by("token_number")

        updated = 0
        for token in tokens:
            self.update_token_estimate(token)
            updated += 1

        return updated