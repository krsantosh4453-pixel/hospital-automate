from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.conf import settings

from .models import (
    AIAgent,
    AgentExecution,
    AgentMemory,
    WorkflowDefinition,
    WorkflowExecution,
    RAGDocument,
    RAGCollection,
    ClinicalEntity,
    ToolDefinition,
    ToolInvocation,
    SafetyViolation,
    AIPromptTemplate,
    ModelProvider,
    CostTracking,
    AuditEvent,
)


@receiver(post_save, sender=AIAgent)
def agent_post_save(sender, instance, created, **kwargs):
    if created:
        AuditEvent.objects.create(
            event_type="agent_created",
            actor=instance.created_by,
            hospital=instance.hospital,
            resource_type="agent",
            resource_id=str(instance.id),
            details={"name": instance.name, "type": instance.agent_type},
        )


@receiver(post_save, sender=AgentExecution)
def execution_post_save(sender, instance, created, **kwargs):
    if created:
        AuditEvent.objects.create(
            event_type="execution_started",
            actor=instance.triggered_by,
            hospital=instance.hospital,
            resource_type="execution",
            resource_id=str(instance.id),
            details={"agent_id": str(instance.agent_id), "status": instance.status},
        )
    elif instance.status in ["completed", "failed", "cancelled"]:
        AuditEvent.objects.create(
            event_type=f"execution_{instance.status}",
            actor=instance.triggered_by,
            hospital=instance.hospital,
            resource_type="execution",
            resource_id=str(instance.id),
            details={
                "agent_id": str(instance.agent_id),
                "duration_ms": instance.duration_ms,
                "tokens_used": instance.tokens_used,
                "cost_usd": float(instance.cost_usd) if instance.cost_usd else 0,
            },
        )


@receiver(post_save, sender=ToolInvocation)
def tool_invocation_post_save(sender, instance, created, **kwargs):
    if created:
        AuditEvent.objects.create(
            event_type="tool_invoked",
            actor=instance.execution.triggered_by if instance.execution else None,
            hospital=instance.execution.hospital if instance.execution else None,
            resource_type="tool",
            resource_id=str(instance.id),
            details={
                "tool_name": instance.tool.name,
                "execution_id": str(instance.execution_id),
                "status": instance.status,
            },
        )


@receiver(post_save, sender=SafetyViolation)
def safety_violation_post_save(sender, instance, created, **kwargs):
    if created:
        AuditEvent.objects.create(
            event_type="safety_violation",
            actor=instance.detected_by,
            hospital=instance.hospital,
            resource_type="safety",
            resource_id=str(instance.id),
            details={
                "violation_type": instance.violation_type,
                "severity": instance.severity,
                "agent_id": str(instance.agent_id) if instance.agent_id else None,
                "execution_id": str(instance.execution_id) if instance.execution_id else None,
            },
        )


@receiver(post_save, sender=CostTracking)
def cost_tracking_post_save(sender, instance, created, **kwargs):
    if instance.cost_usd and instance.cost_usd > getattr(settings, "AI_COST_ALERT_THRESHOLD_USD", 10.0):
        AuditEvent.objects.create(
            event_type="cost_alert",
            actor=None,
            hospital=instance.hospital,
            resource_type="cost",
            resource_id=str(instance.id),
            details={
                "amount_usd": float(instance.cost_usd),
                "provider": instance.provider,
                "model": instance.model,
                "operation": instance.operation,
            },
        )