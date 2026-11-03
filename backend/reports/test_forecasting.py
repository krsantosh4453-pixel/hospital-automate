"""Baseline forecasts: daily totals are real per-day sums, and every method handles any horizon."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from billing.models import Invoice, Payment
from hospital.models import Hospital
from patients.models import Patient
from reports.forecasting import ForecastingService

HISTORY_DAYS = 21


def at_noon(day, minute=0):
    return timezone.make_aware(datetime.combine(day, time(12, minute)))


def weekly_series(days=HISTORY_DAYS):
    """Mondays 10, every other day 2, ending yesterday."""
    end = timezone.localdate() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return [(start + timedelta(days=i), 10.0 if (start + timedelta(days=i)).weekday() == 0 else 2.0)
            for i in range(days)]


class ForecastMethodTests(SimpleTestCase):
    service = ForecastingService(hospital_id=0)

    def test_every_method_returns_one_value_per_requested_day(self):
        series = weekly_series()
        methods = {
            "sma": lambda d: self.service._simple_moving_average(series, forecast_days=d),
            "wma": lambda d: self.service._weighted_moving_average(series, forecast_days=d),
            "trend": lambda d: self.service._linear_trend(series, forecast_days=d),
            "seasonal": lambda d: self.service._seasonal_naive(series, forecast_days=d),
        }
        for name, run in methods.items():
            for days in (1, 7, 14, 30):
                with self.subTest(method=name, days=days):
                    result, error = run(days)
                    self.assertIsNone(error)
                    self.assertEqual(len(result["forecast"]), days)
                    self.assertEqual(len(result["lower_bound"]), days)
                    self.assertEqual(len(result["upper_bound"]), days)
                    for low, mid, high in zip(result["lower_bound"], result["forecast"], result["upper_bound"]):
                        self.assertLessEqual(low, mid)
                        self.assertLessEqual(mid, high)

    def test_seasonal_naive_repeats_the_weekly_pattern_beyond_one_week(self):
        series = weekly_series()
        result, _ = self.service._seasonal_naive(series, forecast_days=14)
        first_forecast_day = series[-1][0] + timedelta(days=1)
        for i, value in enumerate(result["forecast"]):
            expected = 10.0 if (first_forecast_day + timedelta(days=i)).weekday() == 0 else 2.0
            self.assertEqual(value, expected, f"day {i}")

    def test_short_history_is_reported_not_forecast(self):
        series = weekly_series(days=5)
        for run in (self.service._simple_moving_average, self.service._weighted_moving_average,
                    self.service._linear_trend, self.service._seasonal_naive):
            with self.subTest(method=run.__name__):
                result, error = run(series)
                self.assertIsNone(result)
                self.assertEqual(error, "INSUFFICIENT DATA FOR RELIABLE FORECAST")

    def test_flat_history_gives_flat_trend(self):
        series = [(timezone.localdate() - timedelta(days=i), 4.0) for i in range(20, 0, -1)]
        result, error = self.service._linear_trend(series, forecast_days=3)
        self.assertIsNone(error)
        self.assertEqual(result["forecast"], [4.0, 4.0, 4.0])
        self.assertEqual(result["slope"], 0)


class DailySeriesTests(TestCase):
    """Timestamp fields must be summed per calendar day, not one row per timestamp."""

    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Forecast Hospital", is_active=True)
        cls.service = ForecastingService(cls.hospital.id)
        cls.days = [timezone.localdate() - timedelta(days=i) for i in range(HISTORY_DAYS, 0, -1)]

    def test_three_registrations_a_day_count_as_three(self):
        for d_index, day in enumerate(self.days):
            for n in range(3):
                patient = Patient.objects.create(
                    name=f"Synthetic Forecast {d_index}-{n}", age=30, gender="Female",
                    phone=f"91{d_index:04d}{n:04d}", hospital=self.hospital,
                )
                Patient.objects.filter(pk=patient.pk).update(created_at=at_noon(day, n))

        series = self.service._get_daily_series(
            Patient.objects.filter(hospital_id=self.hospital.id), "created_at", days=30
        )
        by_day = dict(series)
        for day in self.days:
            self.assertEqual(by_day[day], 3.0, day)

        result = self.service.forecast_patient_registrations(forecast_days=7, method="sma")
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["forecast"], [3.0] * 7)

    def test_revenue_sums_every_payment_of_the_day(self):
        patient = Patient.objects.create(
            name="Synthetic Revenue Patient", age=40, gender="Male", phone="9100009999", hospital=self.hospital
        )
        invoice = Invoice.objects.create(
            patient=patient, hospital=self.hospital, invoice_number="FC-REV-1", total=Decimal("100000")
        )
        for day in self.days:
            for minute, amount in ((0, "100.00"), (5, "250.00")):
                payment = Payment.objects.create(invoice=invoice, amount=Decimal(amount))
                Payment.objects.filter(pk=payment.pk).update(paid_at=at_noon(day, minute))

        result = self.service.forecast_revenue(forecast_days=10, method="sma")
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["forecast"], [350.0] * 10)

    def test_auto_forecast_longer_than_a_week_does_not_crash(self):
        for d_index, day in enumerate(self.days):
            patient = Patient.objects.create(
                name=f"Synthetic Auto {d_index}", age=30, gender="Male",
                phone=f"92{d_index:08d}", hospital=self.hospital,
            )
            Patient.objects.filter(pk=patient.pk).update(created_at=at_noon(day))

        result = self.service.forecast_patient_registrations(forecast_days=30, method="auto")
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(len(result["forecast"]), 30)
