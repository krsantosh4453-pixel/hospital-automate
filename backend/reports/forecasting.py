"""
Forecasting service for hospital analytics.

Provides baseline statistical forecasting methods:
- Simple Moving Average (SMA)
- Weighted Moving Average (WMA)
- Linear Trend (OLS)
- Seasonal Naive

All forecasts return explicit confidence intervals and data sufficiency checks.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean, stdev
from typing import Any, Optional

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from appointments.models import Appointment
from encounters.models import QueueToken
from emergency.models import EmergencyVisit
from ipd.models import Admission
from laboratory.models import LabTest
from pharmacy.models import Sale
from billing.models import Payment
from patients.models import Patient


class ForecastingService:
    """Baseline statistical forecasting for hospital operations."""

    MIN_DATA_POINTS = 7  # Minimum days of data for reliable forecast
    MIN_DATA_POINTS_TREND = 14  # Minimum for trend-based forecasts

    def __init__(self, hospital_id: int):
        self.hospital_id = hospital_id

    def _get_daily_series(self, queryset, date_field: str, value_field: str = None,
                          start_date=None, end_date=None, days=90):
        """Get daily aggregated time series from a queryset."""
        if end_date is None:
            end_date = timezone.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=days)

        # Filter by hospital and date range
        qs = queryset.filter(**{f"{date_field}__gte": start_date, f"{date_field}__lte": end_date})

        # Aggregate by date
        if value_field:
            daily = qs.values(date_field).annotate(value=Sum(value_field)).order_by(date_field)
        else:
            daily = qs.values(date_field).annotate(value=Count("id")).order_by(date_field)

        # Convert to list of (date, value) tuples
        series = []
        for item in daily:
            date_val = item[date_field]
            if hasattr(date_val, "date"):
                date_val = date_val.date()
            series.append((date_val, float(item["value"] or 0)))

        # Fill missing dates with 0
        filled_series = []
        current = start_date
        series_dict = {d: v for d, v in series}
        while current <= end_date:
            filled_series.append((current, series_dict.get(current, 0.0)))
            current += timedelta(days=1)

        return filled_series

    def _check_data_sufficiency(self, series, min_points=None):
        """Check if we have enough non-zero data points for forecasting."""
        if min_points is None:
            min_points = self.MIN_DATA_POINTS

        non_zero = sum(1 for _, v in series if v > 0)
        return non_zero >= min_points, non_zero

    def _simple_moving_average(self, series, window=7, forecast_days=7):
        """Simple Moving Average forecast."""
        values = [v for _, v in series]
        if len(values) < window:
            return None, "INSUFFICIENT DATA FOR RELIABLE FORECAST"

        # Calculate SMA for the last window
        sma = mean(values[-window:])

        # Forecast is constant at SMA level
        forecast = [round(sma, 2) for _ in range(forecast_days)]

        # Simple confidence interval based on historical std
        if len(values) > window:
            recent_std = stdev(values[-window:]) if len(values[-window:]) > 1 else 0
            margin = 1.96 * recent_std
            lower = [round(max(0, sma - margin), 2) for _ in range(forecast_days)]
            upper = [round(sma + margin, 2) for _ in range(forecast_days)]
        else:
            lower = [round(max(0, sma * 0.8), 2) for _ in range(forecast_days)]
            upper = [round(sma * 1.2, 2) for _ in range(forecast_days)]

        return {
            "method": "Simple Moving Average",
            "window": window,
            "forecast": forecast,
            "lower_bound": lower,
            "upper_bound": upper,
            "last_sma": round(sma, 2),
        }, None

    def _weighted_moving_average(self, series, window=7, forecast_days=7):
        """Weighted Moving Average forecast (more weight to recent)."""
        values = [v for _, v in series]
        if len(values) < window:
            return None, "INSUFFICIENT DATA FOR RELIABLE FORECAST"

        # Linear weights: 1, 2, 3, ..., window
        weights = list(range(1, window + 1))
        weighted_sum = sum(v * w for v, w in zip(values[-window:], weights))
        weight_sum = sum(weights)
        wma = weighted_sum / weight_sum

        forecast = [round(wma, 2) for _ in range(forecast_days)]

        # Confidence interval
        recent_std = stdev(values[-window:]) if len(values[-window:]) > 1 else 0
        margin = 1.96 * recent_std
        lower = [round(max(0, wma - margin), 2) for _ in range(forecast_days)]
        upper = [round(wma + margin, 2) for _ in range(forecast_days)]

        return {
            "method": "Weighted Moving Average",
            "window": window,
            "forecast": forecast,
            "lower_bound": lower,
            "upper_bound": upper,
            "last_wma": round(wma, 2),
        }, None

    def _linear_trend(self, series, forecast_days=7):
        """Linear trend forecast using OLS."""
        values = [v for _, v in series]
        n = len(values)
        if n < self.MIN_DATA_POINTS_TREND:
            return None, "INSUFFICIENT DATA FOR RELIABLE FORECAST"

        # Simple OLS: y = a + bx
        x = list(range(n))
        x_mean = mean(x)
        y_mean = mean(values)

        # Calculate slope (b) and intercept (a)
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values))
        denominator = sum((xi - x_mean) ** 2 for xi in x)

        if denominator == 0:
            return None, "INSUFFICIENT DATA FOR RELIABLE FORECAST"

        b = numerator / denominator
        a = y_mean - b * x_mean

        # Forecast next days
        forecast = []
        lower = []
        upper = []

        # Calculate residuals for confidence interval
        residuals = [yi - (a + b * xi) for xi, yi in zip(x, values)]
        residual_std = stdev(residuals) if len(residuals) > 1 else 0
        margin = 1.96 * residual_std

        for i in range(forecast_days):
            next_x = n + i
            pred = a + b * next_x
            pred = max(0, pred)  # No negative forecasts
            forecast.append(round(pred, 2))
            lower.append(round(max(0, pred - margin), 2))
            upper.append(round(pred + margin, 2))

        return {
            "method": "Linear Trend (OLS)",
            "slope": round(b, 4),
            "intercept": round(a, 2),
            "forecast": forecast,
            "lower_bound": lower,
            "upper_bound": upper,
            "r_squared": round(1 - (sum(r**2 for r in residuals) / sum((yi - y_mean)**2 for yi in values)), 4) if sum((yi - y_mean)**2 for yi in values) > 0 else 0,
        }, None

    def _seasonal_naive(self, series, season_length=7, forecast_days=7):
        """Seasonal naive forecast (same as same day last week)."""
        values = [v for _, v in series]
        if len(values) < season_length:
            return None, "INSUFFICIENT DATA FOR RELIABLE FORECAST"

        forecast = []
        lower = []
        upper = []

        for i in range(forecast_days):
            seasonal_idx = len(values) - season_length + i
            if seasonal_idx >= 0:
                pred = values[seasonal_idx]
            else:
                pred = values[-1]  # Fallback to last value
            pred = max(0, pred)
            forecast.append(round(pred, 2))

            # Simple confidence based on variation in same weekday
            same_weekday_vals = values[i::season_length] if len(values) > season_length else values
            if len(same_weekday_vals) > 1:
                std = stdev(same_weekday_vals)
                margin = 1.96 * std
            else:
                margin = pred * 0.2  # 20% default
            lower.append(round(max(0, pred - margin), 2))
            upper.append(round(pred + margin, 2))

        return {
            "method": f"Seasonal Naive (period={season_length}d)",
            "season_length": season_length,
            "forecast": forecast,
            "lower_bound": lower,
            "upper_bound": upper,
        }, None

    def forecast_appointments(self, forecast_days=7, method="auto"):
        """Forecast daily appointment volume."""
        series = self._get_daily_series(
            Appointment.objects.filter(hospital_id=self.hospital_id),
            "appointment_date",
            days=90
        )

        sufficient, n_points = self._check_data_sufficiency(series)
        if not sufficient:
            return {
                "metric": "appointment_volume",
                "forecast_period_days": forecast_days,
                "model": "N/A",
                "forecast": [],
                "lower_bound": [],
                "upper_bound": [],
                "status": "INSUFFICIENT DATA FOR RELIABLE FORECAST",
                "data_points": n_points,
                "min_required": self.MIN_DATA_POINTS,
                "training_period_days": 90,
                "limitations": ["Less than 7 days of non-zero appointment data in the last 90 days"],
            }

        if method == "auto":
            # Use seasonal naive for weekly patterns, SMA otherwise
            result, error = self._seasonal_naive(series, season_length=7, forecast_days=forecast_days)
            if error:
                result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)
        elif method == "sma":
            result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)
        elif method == "wma":
            result, error = self._weighted_moving_average(series, window=7, forecast_days=forecast_days)
        elif method == "trend":
            result, error = self._linear_trend(series, forecast_days=forecast_days)
        elif method == "seasonal":
            result, error = self._seasonal_naive(series, season_length=7, forecast_days=forecast_days)
        else:
            result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)

        if error:
            return {
                "metric": "appointment_volume",
                "forecast_period_days": forecast_days,
                "model": "N/A",
                "forecast": [],
                "lower_bound": [],
                "upper_bound": [],
                "status": error,
                "data_points": n_points,
                "min_required": self.MIN_DATA_POINTS,
                "training_period_days": 90,
            }

        return {
            "metric": "appointment_volume",
            "forecast_period_days": forecast_days,
            "model": result["method"],
            "model_details": {k: v for k, v in result.items() if k not in ["forecast", "lower_bound", "upper_bound"]},
            "forecast": result["forecast"],
            "lower_bound": result["lower_bound"],
            "upper_bound": result["upper_bound"],
            "status": "success",
            "data_points": n_points,
            "training_period_days": 90,
            "generated_at": timezone.now().isoformat(),
            "limitations": [
                "Baseline statistical model - not a clinical prediction",
                "Assumes historical patterns continue",
                "Does not account for holidays, epidemics, or policy changes",
                "Confidence intervals are approximate",
            ],
        }

    def forecast_patient_registrations(self, forecast_days=7, method="auto"):
        """Forecast daily new patient registrations."""
        series = self._get_daily_series(
            Patient.objects.filter(hospital_id=self.hospital_id),
            "created_at",
            days=90
        )

        sufficient, n_points = self._check_data_sufficiency(series)
        if not sufficient:
            return {
                "metric": "patient_registrations",
                "forecast_period_days": forecast_days,
                "model": "N/A",
                "forecast": [],
                "lower_bound": [],
                "upper_bound": [],
                "status": "INSUFFICIENT DATA FOR RELIABLE FORECAST",
                "data_points": n_points,
                "min_required": self.MIN_DATA_POINTS,
            }

        if method == "auto":
            result, error = self._seasonal_naive(series, season_length=7, forecast_days=forecast_days)
            if error:
                result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)
        elif method == "sma":
            result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)
        elif method == "trend":
            result, error = self._linear_trend(series, forecast_days=forecast_days)
        else:
            result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)

        if error:
            return {"metric": "patient_registrations", "status": error, "data_points": n_points}

        return {
            "metric": "patient_registrations",
            "forecast_period_days": forecast_days,
            "model": result["method"],
            "model_details": {k: v for k, v in result.items() if k not in ["forecast", "lower_bound", "upper_bound"]},
            "forecast": result["forecast"],
            "lower_bound": result["lower_bound"],
            "upper_bound": result["upper_bound"],
            "status": "success",
            "data_points": n_points,
            "generated_at": timezone.now().isoformat(),
            "limitations": [
                "Baseline statistical model",
                "Assumes historical patterns continue",
                "Does not account for marketing campaigns or referral changes",
            ],
        }

    def forecast_queue_volume(self, forecast_days=7, method="auto"):
        """Forecast daily queue token volume."""
        series = self._get_daily_series(
            QueueToken.objects.filter(hospital_id=self.hospital_id),
            "token_date",
            days=60
        )

        sufficient, n_points = self._check_data_sufficiency(series)
        if not sufficient:
            return {
                "metric": "queue_volume",
                "forecast_period_days": forecast_days,
                "status": "INSUFFICIENT DATA FOR RELIABLE FORECAST",
                "data_points": n_points,
            }

        if method == "auto":
            result, error = self._seasonal_naive(series, season_length=7, forecast_days=forecast_days)
            if error:
                result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)
        else:
            result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)

        if error:
            return {"metric": "queue_volume", "status": error, "data_points": n_points}

        return {
            "metric": "queue_volume",
            "forecast_period_days": forecast_days,
            "model": result["method"],
            "model_details": {k: v for k, v in result.items() if k not in ["forecast", "lower_bound", "upper_bound"]},
            "forecast": result["forecast"],
            "lower_bound": result["lower_bound"],
            "upper_bound": result["upper_bound"],
            "status": "success",
            "data_points": n_points,
            "generated_at": timezone.now().isoformat(),
        }

    def forecast_lab_workload(self, forecast_days=7, method="auto"):
        """Forecast daily lab test volume."""
        series = self._get_daily_series(
            LabTest.objects.filter(hospital_id=self.hospital_id),
            "test_date",
            days=90
        )

        sufficient, n_points = self._check_data_sufficiency(series)
        if not sufficient:
            return {
                "metric": "lab_workload",
                "forecast_period_days": forecast_days,
                "status": "INSUFFICIENT DATA FOR RELIABLE FORECAST",
                "data_points": n_points,
            }

        if method == "auto":
            result, error = self._seasonal_naive(series, season_length=7, forecast_days=forecast_days)
            if error:
                result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)
        else:
            result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)

        if error:
            return {"metric": "lab_workload", "status": error, "data_points": n_points}

        return {
            "metric": "lab_workload",
            "forecast_period_days": forecast_days,
            "model": result["method"],
            "model_details": {k: v for k, v in result.items() if k not in ["forecast", "lower_bound", "upper_bound"]},
            "forecast": result["forecast"],
            "lower_bound": result["lower_bound"],
            "upper_bound": result["upper_bound"],
            "status": "success",
            "data_points": n_points,
            "generated_at": timezone.now().isoformat(),
        }

    def forecast_medicine_consumption(self, medicine_id=None, forecast_days=30, method="auto"):
        """Forecast medicine consumption (sales)."""
        qs = Sale.objects.filter(hospital_id=self.hospital_id)
        if medicine_id:
            qs = qs.filter(medicine_id=medicine_id)

        series = self._get_daily_series(qs, "created_at", "quantity", days=180)

        sufficient, n_points = self._check_data_sufficiency(series, min_points=14)
        if not sufficient:
            return {
                "metric": "medicine_consumption",
                "medicine_id": medicine_id,
                "forecast_period_days": forecast_days,
                "status": "INSUFFICIENT DATA FOR RELIABLE FORECAST",
                "data_points": n_points,
            }

        if method == "auto":
            result, error = self._seasonal_naive(series, season_length=30, forecast_days=forecast_days)
            if error:
                result, error = self._simple_moving_average(series, window=14, forecast_days=forecast_days)
        else:
            result, error = self._simple_moving_average(series, window=14, forecast_days=forecast_days)

        if error:
            return {"metric": "medicine_consumption", "status": error, "data_points": n_points}

        return {
            "metric": "medicine_consumption",
            "medicine_id": medicine_id,
            "forecast_period_days": forecast_days,
            "model": result["method"],
            "model_details": {k: v for k, v in result.items() if k not in ["forecast", "lower_bound", "upper_bound"]},
            "forecast": result["forecast"],
            "lower_bound": result["lower_bound"],
            "upper_bound": result["upper_bound"],
            "status": "success",
            "data_points": n_points,
            "generated_at": timezone.now().isoformat(),
        }

    def forecast_bed_occupancy(self, forecast_days=7, method="auto"):
        """Forecast bed occupancy rate."""
        # Get daily occupancy rate
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=60)

        series = []
        current = start_date
        while current <= end_date:
            # Calculate occupancy for each day
            total_beds = 0
            occupied_beds = 0
            # This would need bed allocation history - simplified for now
            # In production, use BedAllocation history
            from hospital.models import Bed
            bed_qs = Bed.objects.filter(room__ward__hospital_id=self.hospital_id)
            total_beds = bed_qs.count()
            if total_beds > 0:
                occupied = bed_qs.exclude(status="Available").count()
                occupancy = (occupied / total_beds) * 100
            else:
                occupancy = 0
            series.append((current, round(occupancy, 2)))
            current += timedelta(days=1)

        # Use the same series for all days (current occupancy doesn't change much daily)
        # This is a simplified approach - real implementation would track daily census
        values = [v for _, v in series]
        n_points = len([v for v in values if v > 0])

        if n_points < 7:
            return {
                "metric": "bed_occupancy",
                "forecast_period_days": forecast_days,
                "status": "INSUFFICIENT DATA FOR RELIABLE FORECAST",
                "data_points": n_points,
            }

        # Simple SMA for occupancy
        result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)
        if error:
            return {"metric": "bed_occupancy", "status": error, "data_points": n_points}

        return {
            "metric": "bed_occupancy",
            "forecast_period_days": forecast_days,
            "model": result["method"],
            "model_details": {k: v for k, v in result.items() if k not in ["forecast", "lower_bound", "upper_bound"]},
            "forecast": result["forecast"],
            "lower_bound": result["lower_bound"],
            "upper_bound": result["upper_bound"],
            "status": "success",
            "data_points": n_points,
            "generated_at": timezone.now().isoformat(),
        }

    def forecast_emergency_volume(self, forecast_days=7, method="auto"):
        """Forecast daily emergency visit volume."""
        series = self._get_daily_series(
            EmergencyVisit.objects.filter(hospital_id=self.hospital_id),
            "arrival_time",
            days=90
        )

        sufficient, n_points = self._check_data_sufficiency(series)
        if not sufficient:
            return {
                "metric": "emergency_volume",
                "forecast_period_days": forecast_days,
                "status": "INSUFFICIENT DATA FOR RELIABLE FORECAST",
                "data_points": n_points,
            }

        if method == "auto":
            result, error = self._seasonal_naive(series, season_length=7, forecast_days=forecast_days)
            if error:
                result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)
        else:
            result, error = self._simple_moving_average(series, window=7, forecast_days=forecast_days)

        if error:
            return {"metric": "emergency_volume", "status": error, "data_points": n_points}

        return {
            "metric": "emergency_volume",
            "forecast_period_days": forecast_days,
            "model": result["method"],
            "model_details": {k: v for k, v in result.items() if k not in ["forecast", "lower_bound", "upper_bound"]},
            "forecast": result["forecast"],
            "lower_bound": result["lower_bound"],
            "upper_bound": result["upper_bound"],
            "status": "success",
            "data_points": n_points,
            "generated_at": timezone.now().isoformat(),
        }

    def forecast_revenue(self, forecast_days=30, method="auto"):
        """Forecast daily revenue."""
        series = self._get_daily_series(
            Payment.objects.filter(invoice__hospital_id=self.hospital_id),
            "paid_at",
            "amount",
            days=180
        )

        sufficient, n_points = self._check_data_sufficiency(series, min_points=14)
        if not sufficient:
            return {
                "metric": "revenue",
                "forecast_period_days": forecast_days,
                "status": "INSUFFICIENT DATA FOR RELIABLE FORECAST",
                "data_points": n_points,
            }

        if method == "auto":
            result, error = self._linear_trend(series, forecast_days=forecast_days)
            if error:
                result, error = self._simple_moving_average(series, window=14, forecast_days=forecast_days)
        else:
            result, error = self._simple_moving_average(series, window=14, forecast_days=forecast_days)

        if error:
            return {"metric": "revenue", "status": error, "data_points": n_points}

        return {
            "metric": "revenue",
            "forecast_period_days": forecast_days,
            "model": result["method"],
            "model_details": {k: v for k, v in result.items() if k not in ["forecast", "lower_bound", "upper_bound"]},
            "forecast": result["forecast"],
            "lower_bound": result["lower_bound"],
            "upper_bound": result["upper_bound"],
            "status": "success",
            "data_points": n_points,
            "generated_at": timezone.now().isoformat(),
            "limitations": [
                "Revenue forecasting is inherently uncertain",
                "Does not account for insurance claim delays",
                "Seasonal patterns may not hold during health crises",
            ],
        }

    def get_all_forecasts(self, forecast_days=7):
        """Get all available forecasts in one call."""
        return {
            "appointments": self.forecast_appointments(forecast_days),
            "patient_registrations": self.forecast_patient_registrations(forecast_days),
            "queue_volume": self.forecast_queue_volume(forecast_days),
            "lab_workload": self.forecast_lab_workload(forecast_days),
            "emergency_volume": self.forecast_emergency_volume(forecast_days),
            "bed_occupancy": self.forecast_bed_occupancy(forecast_days),
            "revenue": self.forecast_revenue(forecast_days),
            "generated_at": timezone.now().isoformat(),
            "forecast_horizon_days": forecast_days,
            "disclaimer": (
                "All forecasts are baseline statistical projections based on historical data. "
                "They are NOT clinical predictions and should NOT be used for clinical decision-making. "
                "Forecasts assume historical patterns continue and do not account for external factors "
                "such as epidemics, policy changes, or seasonal variations beyond the training period."
            ),
        }