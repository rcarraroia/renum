"""
Alerting Service
Comprehensive alerting system for errors, thresholds, and system events
"""
from typing import Dict, List, Optional, Any, Callable, Union
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from collections import defaultdict

from app.services.analytics_service import analytics_service
from app.services.performance_monitor import PerformanceAlert, AlertSeverity

logger = logging.getLogger(__name__)

class AlertType(Enum):
    """Types of alerts"""
    PERFORMANCE = "performance"
    ERROR_RATE = "error_rate"
    COST_THRESHOLD = "cost_threshold"
    SYSTEM_RESOURCE = "system_resource"
    INTEGRATION_FAILURE = "integration_failure"
    SECURITY = "security"
    CUSTOM = "custom"

class AlertChannel(Enum):
    """Alert notification channels"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"
    IN_APP = "in_app"

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: Dict[str, Any]  # Condition configuration
    channels: List[AlertChannel]
    enabled: bool = True
    cooldown_minutes: int = 15  # Minimum time between alerts
    auto_resolve_minutes: Optional[int] = None
    tags: Dict[str, str] = None
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    rule_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any]
    status: AlertStatus
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None
    notification_count: int = 0
    last_notification_at: Optional[datetime] = None

class AlertingService:
    """Main alerting service"""
    
    def __init__(self):
        # Alert rules storage
        self.alert_rules: Dict[str, AlertRule] = {}
        
        # Active alerts
        self.active_alerts: Dict[str, Alert] = {}
        
        # Alert history (in-memory for demo, would use database in production)
        self.alert_history: List[Alert] = []
        
        # Notification handlers
        self.notification_handlers: Dict[AlertChannel, Callable] = {}
        
        # Alert suppression rules
        self.suppression_rules: List[Dict[str, Any]] = []
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Initialize default alert rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self) -> None:
        """Initialize default alert rules"""
        default_rules = [
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate",
                description="Alert when API error rate exceeds threshold",
                alert_type=AlertType.ERROR_RATE,
                severity=AlertSeverity.HIGH,
                condition={
                    "metric": "api_error_rate_percent",
                    "threshold": 10.0,
                    "window_minutes": 5,
                    "operator": ">"
                },
                channels=[AlertChannel.EMAIL, AlertChannel.IN_APP],
                cooldown_minutes=10
            ),
            AlertRule(
                rule_id="agent_execution_failures",
                name="Agent Execution Failures",
                description="Alert when agent execution failure rate is high",
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.MEDIUM,
                condition={
                    "metric": "agent_failure_rate_percent",
                    "threshold": 15.0,
                    "window_minutes": 10,
                    "operator": ">"
                },
                channels=[AlertChannel.EMAIL, AlertChannel.IN_APP],
                cooldown_minutes=15
            ),
            AlertRule(
                rule_id="high_response_time",
                name="High API Response Time",
                description="Alert when API response time is consistently high",
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.MEDIUM,
                condition={
                    "metric": "api_response_time_ms",
                    "threshold": 5000,
                    "window_minutes": 5,
                    "operator": ">",
                    "min_samples": 10
                },
                channels=[AlertChannel.IN_APP],
                cooldown_minutes=20
            ),
            AlertRule(
                rule_id="system_cpu_high",
                name="High CPU Usage",
                description="Alert when system CPU usage is critically high",
                alert_type=AlertType.SYSTEM_RESOURCE,
                severity=AlertSeverity.CRITICAL,
                condition={
                    "metric": "system_cpu_usage_percent",
                    "threshold": 90.0,
                    "window_minutes": 3,
                    "operator": ">"
                },
                channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK, AlertChannel.IN_APP],
                cooldown_minutes=5
            ),
            AlertRule(
                rule_id="system_memory_high",
                name="High Memory Usage",
                description="Alert when system memory usage is critically high",
                alert_type=AlertType.SYSTEM_RESOURCE,
                severity=AlertSeverity.CRITICAL,
                condition={
                    "metric": "system_memory_usage_percent",
                    "threshold": 95.0,
                    "window_minutes": 3,
                    "operator": ">"
                },
                channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK, AlertChannel.IN_APP],
                cooldown_minutes=5
            ),
            AlertRule(
                rule_id="integration_failure_spike",
                name="Integration Failure Spike",
                description="Alert when integration failures spike",
                alert_type=AlertType.INTEGRATION_FAILURE,
                severity=AlertSeverity.HIGH,
                condition={
                    "metric": "integration_failure_count",
                    "threshold": 20,
                    "window_minutes": 10,
                    "operator": ">"
                },
                channels=[AlertChannel.EMAIL, AlertChannel.IN_APP],
                cooldown_minutes=15
            )
        ]
        
        for rule in default_rules:
            rule.created_at = datetime.utcnow()
            rule.updated_at = datetime.utcnow()
            rule.tags = rule.tags or {}
            self.alert_rules[rule.rule_id] = rule
    
    def add_notification_handler(
        self,
        channel: AlertChannel,
        handler: Callable[[Alert], None]
    ) -> None:
        """Add notification handler for a channel"""
        self.notification_handlers[channel] = handler
    
    async def start_monitoring(self) -> None:
        """Start alert monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            return
        
        self.monitoring_task = asyncio.create_task(self._monitor_alerts())
        self.cleanup_task = asyncio.create_task(self._cleanup_alerts())
        
        logger.info("Alert monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop alert monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        logger.info("Alert monitoring stopped")
    
    async def _monitor_alerts(self) -> None:
        """Background task to monitor alert conditions"""
        while True:
            try:
                for rule in self.alert_rules.values():
                    if rule.enabled:
                        await self._check_alert_rule(rule)
                
                # Check for auto-resolve conditions
                await self._check_auto_resolve()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in alert monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _cleanup_alerts(self) -> None:
        """Background task to cleanup old alerts"""
        while True:
            try:
                # Clean up resolved alerts older than 7 days
                cutoff_time = datetime.utcnow() - timedelta(days=7)
                
                self.alert_history = [
                    alert for alert in self.alert_history
                    if alert.resolved_at is None or alert.resolved_at > cutoff_time
                ]
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in alert cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def _check_alert_rule(self, rule: AlertRule) -> None:
        """Check if alert rule condition is met"""
        try:
            condition = rule.condition
            metric_name = condition.get('metric')
            threshold = condition.get('threshold')
            window_minutes = condition.get('window_minutes', 5)
            operator = condition.get('operator', '>')
            min_samples = condition.get('min_samples', 1)
            
            # Get metric data for the window
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=window_minutes)
            
            metric_stats = await analytics_service.metrics_collector.get_metric_stats(
                metric_name,
                start_time,
                end_time
            )
            
            # Check if we have enough samples
            if metric_stats['count'] < min_samples:
                return
            
            # Get the value to compare (using average for most metrics)
            if metric_name.endswith('_count'):
                value = metric_stats['sum']  # Use sum for count metrics
            else:
                value = metric_stats['avg']  # Use average for other metrics
            
            # Check condition
            condition_met = False
            if operator == '>':
                condition_met = value > threshold
            elif operator == '<':
                condition_met = value < threshold
            elif operator == '>=':
                condition_met = value >= threshold
            elif operator == '<=':
                condition_met = value <= threshold
            elif operator == '==':
                condition_met = value == threshold
            
            if condition_met:
                await self._trigger_alert(rule, value, metric_stats)
            else:
                # Check if we should resolve an existing alert
                await self._check_alert_resolution(rule, value)
                
        except Exception as e:
            logger.error(f"Error checking alert rule {rule.rule_id}: {e}")
    
    async def _trigger_alert(
        self,
        rule: AlertRule,
        current_value: float,
        metric_stats: Dict[str, Any]
    ) -> None:
        """Trigger an alert"""
        # Check if alert is in cooldown
        existing_alert = None
        for alert in self.active_alerts.values():
            if (alert.rule_id == rule.rule_id and 
                alert.status == AlertStatus.ACTIVE):
                existing_alert = alert
                break
        
        if existing_alert:
            # Check cooldown
            if (existing_alert.last_notification_at and
                datetime.utcnow() - existing_alert.last_notification_at < 
                timedelta(minutes=rule.cooldown_minutes)):
                return
            
            # Update existing alert
            existing_alert.notification_count += 1
            existing_alert.last_notification_at = datetime.utcnow()
            existing_alert.updated_at = datetime.utcnow()
            existing_alert.details.update({
                'current_value': current_value,
                'metric_stats': metric_stats
            })
            
            await self._send_notifications(existing_alert)
            return
        
        # Create new alert
        alert = Alert(
            alert_id=str(uuid4()),
            rule_id=rule.rule_id,
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=rule.name,
            message=f"{rule.description}. Current value: {current_value:.2f}, Threshold: {rule.condition['threshold']}",
            details={
                'rule_name': rule.name,
                'condition': rule.condition,
                'current_value': current_value,
                'metric_stats': metric_stats,
                'window_minutes': rule.condition.get('window_minutes', 5)
            },
            status=AlertStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            notification_count=1,
            last_notification_at=datetime.utcnow()
        )
        
        self.active_alerts[alert.alert_id] = alert
        
        # Send notifications
        await self._send_notifications(alert)
        
        # Record alert metric
        await analytics_service.metrics_collector.record_metric(
            'alert_triggered',
            1,
            {
                'rule_id': rule.rule_id,
                'alert_type': rule.alert_type.value,
                'severity': rule.severity.value
            }
        )
        
        logger.warning(f"Alert triggered: {alert.title} - {alert.message}")
    
    async def _send_notifications(self, alert: Alert) -> None:
        """Send alert notifications through configured channels"""
        rule = self.alert_rules.get(alert.rule_id)
        if not rule:
            return
        
        for channel in rule.channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    await asyncio.create_task(self._call_handler(handler, alert))
                except Exception as e:
                    logger.error(f"Error sending notification via {channel.value}: {e}")
    
    async def _call_handler(self, handler: Callable, alert: Alert) -> None:
        """Call notification handler (async wrapper)"""
        if asyncio.iscoroutinefunction(handler):
            await handler(alert)
        else:
            handler(alert)
    
    async def _check_alert_resolution(self, rule: AlertRule, current_value: float) -> None:
        """Check if alert should be auto-resolved"""
        if not rule.auto_resolve_minutes:
            return
        
        # Find active alerts for this rule
        for alert in list(self.active_alerts.values()):
            if (alert.rule_id == rule.rule_id and 
                alert.status == AlertStatus.ACTIVE):
                
                # Check if condition is no longer met for auto-resolve period
                time_since_created = datetime.utcnow() - alert.created_at
                if time_since_created >= timedelta(minutes=rule.auto_resolve_minutes):
                    await self.resolve_alert(alert.alert_id, auto_resolved=True)
    
    async def _check_auto_resolve(self) -> None:
        """Check for alerts that should be auto-resolved"""
        for alert in list(self.active_alerts.values()):
            rule = self.alert_rules.get(alert.rule_id)
            if rule and rule.auto_resolve_minutes:
                time_since_updated = datetime.utcnow() - alert.updated_at
                if time_since_updated >= timedelta(minutes=rule.auto_resolve_minutes):
                    await self.resolve_alert(alert.alert_id, auto_resolved=True)
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: UUID,
        note: Optional[str] = None
    ) -> bool:
        """Acknowledge an alert"""
        alert = self.active_alerts.get(alert_id)
        if not alert or alert.status != AlertStatus.ACTIVE:
            return False
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        alert.updated_at = datetime.utcnow()
        
        if note:
            alert.details['acknowledgment_note'] = note
        
        logger.info(f"Alert acknowledged: {alert.title} by {acknowledged_by}")
        return True
    
    async def resolve_alert(
        self,
        alert_id: str,
        resolved_by: Optional[UUID] = None,
        note: Optional[str] = None,
        auto_resolved: bool = False
    ) -> bool:
        """Resolve an alert"""
        alert = self.active_alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = resolved_by
        alert.updated_at = datetime.utcnow()
        
        if note:
            alert.details['resolution_note'] = note
        
        if auto_resolved:
            alert.details['auto_resolved'] = True
        
        # Move to history
        self.alert_history.append(alert)
        del self.active_alerts[alert_id]
        
        # Record resolution metric
        await analytics_service.metrics_collector.record_metric(
            'alert_resolved',
            1,
            {
                'rule_id': alert.rule_id,
                'alert_type': alert.alert_type.value,
                'auto_resolved': str(auto_resolved)
            }
        )
        
        logger.info(f"Alert resolved: {alert.title}")
        return True
    
    async def create_custom_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        details: Optional[Dict[str, Any]] = None,
        channels: Optional[List[AlertChannel]] = None
    ) -> str:
        """Create a custom alert"""
        alert = Alert(
            alert_id=str(uuid4()),
            rule_id="custom",
            alert_type=AlertType.CUSTOM,
            severity=severity,
            title=title,
            message=message,
            details=details or {},
            status=AlertStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            notification_count=1,
            last_notification_at=datetime.utcnow()
        )
        
        self.active_alerts[alert.alert_id] = alert
        
        # Send notifications if channels specified
        if channels:
            for channel in channels:
                handler = self.notification_handlers.get(channel)
                if handler:
                    try:
                        await self._call_handler(handler, alert)
                    except Exception as e:
                        logger.error(f"Error sending custom alert notification: {e}")
        
        return alert.alert_id
    
    async def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None
    ) -> List[Dict[str, Any]]:
        """Get active alerts"""
        alerts = []
        
        for alert in self.active_alerts.values():
            if severity and alert.severity != severity:
                continue
            if alert_type and alert.alert_type != alert_type:
                continue
            
            alerts.append({
                'alert_id': alert.alert_id,
                'rule_id': alert.rule_id,
                'alert_type': alert.alert_type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'status': alert.status.value,
                'created_at': alert.created_at.isoformat(),
                'updated_at': alert.updated_at.isoformat(),
                'notification_count': alert.notification_count,
                'details': alert.details
            })
        
        # Sort by severity and creation time
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3
        }
        
        alerts.sort(key=lambda x: (
            severity_order.get(AlertSeverity(x['severity']), 4),
            x['created_at']
        ))
        
        return alerts
    
    async def get_alert_statistics(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get alert statistics"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Count alerts by type and severity
        alerts_by_type = defaultdict(int)
        alerts_by_severity = defaultdict(int)
        total_alerts = 0
        resolved_alerts = 0
        
        # Check active alerts
        for alert in self.active_alerts.values():
            if alert.created_at >= start_time:
                alerts_by_type[alert.alert_type.value] += 1
                alerts_by_severity[alert.severity.value] += 1
                total_alerts += 1
        
        # Check alert history
        for alert in self.alert_history:
            if alert.created_at >= start_time:
                alerts_by_type[alert.alert_type.value] += 1
                alerts_by_severity[alert.severity.value] += 1
                total_alerts += 1
                if alert.status == AlertStatus.RESOLVED:
                    resolved_alerts += 1
        
        return {
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            },
            'total_alerts': total_alerts,
            'active_alerts': len(self.active_alerts),
            'resolved_alerts': resolved_alerts,
            'resolution_rate_percent': round(
                (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0, 2
            ),
            'alerts_by_type': dict(alerts_by_type),
            'alerts_by_severity': dict(alerts_by_severity),
            'alert_rules_count': len(self.alert_rules),
            'enabled_rules_count': sum(1 for rule in self.alert_rules.values() if rule.enabled)
        }

# Global alerting service instance
alerting_service = AlertingService()

# Default notification handlers
async def default_email_handler(alert: Alert) -> None:
    """Default email notification handler"""
    logger.info(f"EMAIL ALERT: {alert.title} - {alert.message}")

async def default_webhook_handler(alert: Alert) -> None:
    """Default webhook notification handler"""
    logger.info(f"WEBHOOK ALERT: {alert.title} - {alert.message}")

async def default_in_app_handler(alert: Alert) -> None:
    """Default in-app notification handler"""
    logger.info(f"IN-APP ALERT: {alert.title} - {alert.message}")

# Register default handlers
alerting_service.add_notification_handler(AlertChannel.EMAIL, default_email_handler)
alerting_service.add_notification_handler(AlertChannel.WEBHOOK, default_webhook_handler)
alerting_service.add_notification_handler(AlertChannel.IN_APP, default_in_app_handler)