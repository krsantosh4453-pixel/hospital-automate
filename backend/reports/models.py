from django.db import models
from django.conf import settings
import uuid


class MLModel(models.Model):
    """ML Model registry for tracking trained models."""

    class ModelType(models.TextChoices):
        FORECASTING = "forecasting", "Forecasting"
        CLASSIFICATION = "classification", "Classification"
        REGRESSION = "regression", "Regression"
        ANOMALY_DETECTION = "anomaly_detection", "Anomaly Detection"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        TRAINING = "training", "Training"
        TRAINED = "trained", "Trained"
        DEPLOYED = "deployed", "Deployed"
        ARCHIVED = "archived", "Archived"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    model_type = models.CharField(max_length=30, choices=ModelType.choices)
    target_metric = models.CharField(max_length=100, help_text="The KPI/metric being predicted")
    description = models.TextField(blank=True)

    # Model configuration
    algorithm = models.CharField(max_length=100, help_text="e.g., ARIMA, Prophet, XGBoost, LSTM")
    hyperparameters = models.JSONField(default=dict, blank=True)
    features = models.JSONField(default=list, blank=True, help_text="List of feature names")

    # Training data specification
    training_start_date = models.DateField()
    training_end_date = models.DateField()
    validation_start_date = models.DateField(null=True, blank=True)
    validation_end_date = models.DateField(null=True, blank=True)

    # Evaluation metrics
    metrics = models.JSONField(default=dict, blank=True, help_text="MAE, RMSE, MAPE, etc.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Model artifact storage
    model_path = models.CharField(max_length=500, blank=True, help_text="Path to serialized model")
    preprocessing_path = models.CharField(max_length=500, blank=True, help_text="Path to preprocessing pipeline")

    # Versioning
    version = models.CharField(max_length=50)
    parent_model = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_models",
    )

    # Hospital scoping
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="ml_models",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_ml_models",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    trained_at = models.DateTimeField(null=True, blank=True)
    deployed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["hospital", "name", "version"]

    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_model_type_display()})"


class MLPrediction(models.Model):
    """Record of ML predictions for monitoring and audit."""

    model = models.ForeignKey(
        MLModel,
        on_delete=models.CASCADE,
        related_name="predictions",
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="ml_predictions",
    )

    # Prediction details
    prediction_date = models.DateField()
    horizon_days = models.PositiveIntegerField()
    predicted_values = models.JSONField(default=list, help_text="List of predicted values")
    lower_bounds = models.JSONField(default=list, blank=True)
    upper_bounds = models.JSONField(default=list, blank=True)

    # Actual values (filled in later for evaluation)
    actual_values = models.JSONField(default=list, blank=True)
    evaluated = models.BooleanField(default=False)
    evaluation_metrics = models.JSONField(default=dict, blank=True)

    # Metadata
    input_features = models.JSONField(default=dict, blank=True)
    prediction_latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-prediction_date"]
        indexes = [
            models.Index(fields=["model", "prediction_date"]),
            models.Index(fields=["hospital", "prediction_date"]),
        ]

    def __str__(self):
        return f"Prediction for {self.model.name} on {self.prediction_date}"


class MLTrainingJob(models.Model):
    """Track ML training jobs for reproducibility."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        MLModel,
        on_delete=models.CASCADE,
        related_name="training_jobs",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Configuration snapshot
    config_snapshot = models.JSONField(default=dict, help_text="Full training config at job start")

    # Progress tracking
    current_epoch = models.PositiveIntegerField(default=0)
    total_epochs = models.PositiveIntegerField(default=0)
    progress_percent = models.FloatField(default=0.0)

    # Logs and metrics
    training_logs = models.TextField(blank=True)
    final_metrics = models.JSONField(default=dict, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Training job for {self.model.name} ({self.get_status_display()})"


class FeatureStore(models.Model):
    """Feature store for ML-ready features."""

    class FeatureType(models.TextChoices):
        NUMERICAL = "numerical", "Numerical"
        CATEGORICAL = "categorical", "Categorical"
        TEMPORAL = "temporal", "Temporal"
        AGGREGATE = "aggregate", "Aggregate"

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="features",
    )
    name = models.CharField(max_length=150)
    feature_type = models.CharField(max_length=20, choices=FeatureType.choices)
    description = models.TextField(blank=True)

    # Source specification
    source_table = models.CharField(max_length=100, help_text="Django model name")
    source_query = models.TextField(help_text="Query or logic to compute this feature")
    aggregation_window = models.CharField(max_length=50, blank=True, help_text="e.g., 7d, 30d")

    # Feature metadata
    is_active = models.BooleanField(default=True)
    is_derived = models.BooleanField(default=False)
    dependencies = models.JSONField(default=list, blank=True, help_text="Other features this depends on")

    # Statistics
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    mean_value = models.FloatField(null=True, blank=True)
    null_percentage = models.FloatField(default=0.0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_features",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["hospital", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_feature_type_display()})"


class DataPipeline(models.Model):
    """ETL/Feature engineering pipeline definitions."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ERROR = "error", "Error"

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="data_pipelines",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    # Pipeline definition (DAG-like structure)
    steps = models.JSONField(default=list, help_text="Ordered list of transformation steps")

    # Schedule
    schedule_cron = models.CharField(max_length=100, blank=True, help_text="Cron expression for scheduling")
    is_scheduled = models.BooleanField(default=False)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    last_run = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(max_length=20, blank=True)
    last_run_logs = models.TextField(blank=True)

    # Output
    output_table = models.CharField(max_length=100, help_text="Target table/model for pipeline output")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_pipelines",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["hospital", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class DataPipelineRun(models.Model):
    """Execution history for data pipelines."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    pipeline = models.ForeignKey(
        DataPipeline,
        on_delete=models.CASCADE,
        related_name="runs",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Run details
    rows_processed = models.PositiveIntegerField(default=0)
    rows_output = models.PositiveIntegerField(default=0)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Logs
    logs = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Run of {self.pipeline.name} at {self.started_at}"


class ReportTemplate(models.Model):
    """Predefined report templates for common analytics views."""

    class ReportType(models.TextChoices):
        FINANCIAL = "financial", "Financial Report"
        CLINICAL = "clinical", "Clinical Report"
        OPERATIONAL = "operational", "Operational Report"
        PATIENT_SUMMARY = "patient_summary", "Patient Summary"
        DEPARTMENT = "department", "Department Report"
        DOCTOR_PERFORMANCE = "doctor_performance", "Doctor Performance"
        INVENTORY = "inventory", "Inventory Report"
        QUEUE = "queue", "Queue Intelligence"

    class Period(models.TextChoices):
        TODAY = "today", "Today"
        YESTERDAY = "yesterday", "Yesterday"
        LAST_7_DAYS = "last_7_days", "Last 7 Days"
        LAST_30_DAYS = "last_30_days", "Last 30 Days"
        THIS_MONTH = "this_month", "This Month"
        LAST_MONTH = "last_month", "Last Month"
        THIS_YEAR = "this_year", "This Year"
        CUSTOM = "custom", "Custom Range"

    name = models.CharField(max_length=150)
    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    description = models.TextField(blank=True)
    default_period = models.CharField(
        max_length=20, choices=Period.choices, default=Period.LAST_30_DAYS
    )
    filters = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_report_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class SavedReport(models.Model):
    """User-saved report configurations with parameters."""

    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="saved_reports",
    )
    name = models.CharField(max_length=150)
    report_type = models.CharField(max_length=30, choices=ReportTemplate.ReportType.choices)
    period = models.CharField(max_length=20, choices=ReportTemplate.Period.choices)
    custom_start_date = models.DateField(null=True, blank=True)
    custom_end_date = models.DateField(null=True, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_reports",
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="saved_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["name", "created_by", "hospital"]

    def __str__(self):
        return f"{self.name} - {self.hospital.name}"


class ScheduledReport(models.Model):
    """Scheduled report generation and delivery."""

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    class DeliveryMethod(models.TextChoices):
        EMAIL = "email", "Email"
        IN_APP = "in_app", "In-App Notification"
        BOTH = "both", "Email + In-App"

    name = models.CharField(max_length=150)
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="scheduled_reports",
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="scheduled_reports",
    )
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    delivery_method = models.CharField(
        max_length=20, choices=DeliveryMethod.choices, default=DeliveryMethod.IN_APP
    )
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="scheduled_report_subscriptions",
    )
    filters = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_generated = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_scheduled_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class KPISnapshot(models.Model):
    """Historical KPI snapshots for trend analysis."""

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="kpi_snapshots",
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    kpi_name = models.CharField(max_length=100)
    kpi_value = models.DecimalField(max_digits=20, decimal_places=4)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_end"]
        indexes = [
            models.Index(fields=["hospital", "kpi_name", "period_end"]),
        ]
        unique_together = ["hospital", "kpi_name", "period_start", "period_end"]

    def __str__(self):
        return f"{self.hospital.name} - {self.kpi_name} - {self.period_end.date()}"