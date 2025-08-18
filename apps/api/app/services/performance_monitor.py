"""
Performance Monitoring Service
Advanced performance monitoring for agent executions and system resources
"""
from typing import Dict, List, Optional, Any, Callable
from uuid import UUID
from datetime import datetime, timedelta
import asyncio
import time
import psutil
import logging
from dataclasses import dataclass
from enum import Enum

from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class PerformanceAlert:
    """Performance alert data structure"""
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class PerformanceMonitor:
    """Advanced performance monitoring system"""
    
    def __init__(self):
        # Performance thresholds
        self.thresholds = {
            # Agent execution thresholds
            'agent_execution_time_ms': {
                'warning': 5000,    # 5 seconds
                'critical': 15000   # 15 seconds
            },
            'agent_memory_usage_mb': {
                'warning': 500,     # 500 MB
                'critical': 1000    # 1 GB
            },
            'agent_error_rate_percent': {
                'warning': 5.0,     # 5%
                'critical': 15.0    # 15%
            },
            
            # System resource thresholds
            'cpu_usage_percent': {
                'warning': 80.0,    # 80%
                'critical': 95.0    # 95%
            },
            'memory_usage_percent': {
                'warning': 85.0,    # 85%
                'critical': 95.0    # 95%
            },
            'disk_usage_percent': {
                'warning': 85.0,    # 85%
                'critical': 95.0    # 95%
            },
            
            # API performance thresholds
            'api_response_time_ms': {
                'warning': 2000,    # 2 seconds
                'critical': 5000    # 5 seconds
            },
            'api_error_rate_percent': {
                'warning': 5.0,     # 5%
                'critical': 10.0    # 10%
            },
            
            # Integration thresholds
            'webhook_processing_time_ms': {
                'warning': 3000,    # 3 seconds
                'critical': 8000    # 8 seconds
            },
            'integration_failure_rate_percent': {
                'warning': 10.0,    # 10%
                'critical': 25.0    # 25%
            }
        }
        
        # Active alerts
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Monitoring intervals
        self.monitoring_intervals = {
            'system_resources': 30,    # 30 seconds
            'agent_performance': 60,   # 1 minute
            'api_performance': 300,    # 5 minutes
        }
        
        # Background monitoring tasks
        self.monitoring_tasks: List[asyncio.Task] = []
        self.monitoring_active = False
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    async def start_monitoring(self) -> None:
        """Start background monitoring tasks"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._monitor_system_resources()),
            asyncio.create_task(self._monitor_agent_performance()),
            asyncio.create_task(self._monitor_api_performance())
        ]
        
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring tasks"""
        self.monitoring_active = False
        
        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.monitoring_tasks.clear()
        logger.info("Performance monitoring stopped")
    
    async def _monitor_system_resources(self) -> None:
        """Monitor system resource usage"""
        while self.monitoring_active:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Record metrics
                await analytics_service.metrics_collector.record_metric(
                    'system_cpu_usage_percent', cpu_percent
                )
                await analytics_service.metrics_collector.record_metric(
                    'system_memory_usage_percent', memory.percent
                )
                await analytics_service.metrics_collector.record_metric(
                    'system_disk_usage_percent', disk.percent
                )
                
                # Check thresholds
                await self._check_threshold('cpu_usage_percent', cpu_percent)
                await self._check_threshold('memory_usage_percent', memory.percent)
                await self._check_threshold('disk_usage_percent', disk.percent)
                
                await asyncio.sleep(self.monitoring_intervals['system_resources'])
                
            except Exception as e:
                logger.error(f"Error monitoring system resources: {e}")
                await asyncio.sleep(self.monitoring_intervals['system_resources'])
    
    async def _monitor_agent_performance(self) -> None:
        """Monitor agent performance metrics"""
        while self.monitoring_active:
            try:
                # Get recent agent performance data
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(minutes=5)
                
                # This would typically query agent execution data
                # For now, we'll simulate some checks
                
                await asyncio.sleep(self.monitoring_intervals['agent_performance'])
                
            except Exception as e:
                logger.error(f"Error monitoring agent performance: {e}")
                await asyncio.sleep(self.monitoring_intervals['agent_performance'])
    
    async def _monitor_api_performance(self) -> None:
        """Monitor API performance metrics"""
        while self.monitoring_active:
            try:
                # Get recent API performance data
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(minutes=5)
                
                # Get API response time stats
                api_stats = await analytics_service.metrics_collector.get_metric_stats(
                    'api_response_time_ms',
                    start_time,
                    end_time
                )
                
                if api_stats['count'] > 0:
                    avg_response_time = api_stats['avg']
                    await self._check_threshold('api_response_time_ms', avg_response_time)
                
                await asyncio.sleep(self.monitoring_intervals['api_performance'])
                
            except Exception as e:
                logger.error(f"Error monitoring API performance: {e}")
                await asyncio.sleep(self.monitoring_intervals['api_performance'])
    
    async def _check_threshold(self, metric_name: str, value: float) -> None:
        """Check if metric value exceeds thresholds"""
        if metric_name not in self.thresholds:
            return
        
        thresholds = self.thresholds[metric_name]
        alert_id = f"{metric_name}_threshold"
        
        # Determine severity
        severity = None
        if value >= thresholds.get('critical', float('inf')):
            severity = AlertSeverity.CRITICAL
        elif value >= thresholds.get('warning', float('inf')):
            severity = AlertSeverity.MEDIUM
        
        if severity:
            # Create or update alert
            if alert_id not in self.active_alerts or not self.active_alerts[alert_id].resolved:
                alert = PerformanceAlert(
                    alert_id=alert_id,
                    alert_type='threshold_exceeded',
                    severity=severity,
                    message=f"{metric_name} exceeded {severity.value} threshold",
                    details={
                        'metric_name': metric_name,
                        'current_value': value,
                        'threshold_value': thresholds.get(severity.value.replace('medium', 'warning'), 0),
                        'severity': severity.value
                    },
                    timestamp=datetime.utcnow()
                )
                
                self.active_alerts[alert_id] = alert
                await self._trigger_alert(alert)
        else:
            # Resolve alert if it exists
            if alert_id in self.active_alerts and not self.active_alerts[alert_id].resolved:
                self.active_alerts[alert_id].resolved = True
                self.active_alerts[alert_id].resolved_at = datetime.utcnow()
                
                logger.info(f"Alert resolved: {alert_id}")
    
    async def _trigger_alert(self, alert: PerformanceAlert) -> None:
        """Trigger performance alert"""
        logger.warning(f"Performance alert: {alert.message} - {alert.details}")
        
        # Record alert metric
        await analytics_service.metrics_collector.record_metric(
            'performance_alert',
            1,
            {
                'alert_type': alert.alert_type,
                'severity': alert.severity.value,
                'metric_name': alert.details.get('metric_name', 'unknown')
            }
        )
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def record_agent_execution_performance(
        self,
        agent_id: str,
        execution_id: UUID,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        memory_usage_mb: Optional[float] = None,
        error_type: Optional[str] = None,
        cost_cents: Optional[float] = None
    ) -> None:
        """Record detailed agent execution performance"""
        execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Record in analytics service
        await analytics_service.record_agent_execution(
            agent_id=agent_id,
            execution_id=execution_id,
            execution_time_ms=execution_time_ms,
            success=success,
            error_type=error_type,
            cost_cents=cost_cents
        )
        
        # Record memory usage if provided
        if memory_usage_mb is not None:
            await analytics_service.metrics_collector.record_metric(
                'agent_memory_usage_mb',
                memory_usage_mb,
                {'agent_id': agent_id}
            )
        
        # Check performance thresholds
        await self._check_threshold('agent_execution_time_ms', execution_time_ms)
        
        if memory_usage_mb is not None:
            await self._check_threshold('agent_memory_usage_mb', memory_usage_mb)
    
    async def get_performance_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get system analytics
        system_analytics = await analytics_service.get_system_analytics(start_time, end_time)
        
        # Get active alerts
        active_alerts = [
            {
                'alert_id': alert.alert_id,
                'alert_type': alert.alert_type,
                'severity': alert.severity.value,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved
            }
            for alert in self.active_alerts.values()
            if not alert.resolved
        ]
        
        # Get system resource stats
        cpu_stats = await analytics_service.metrics_collector.get_metric_stats(
            'system_cpu_usage_percent', start_time, end_time
        )
        memory_stats = await analytics_service.metrics_collector.get_metric_stats(
            'system_memory_usage_percent', start_time, end_time
        )
        disk_stats = await analytics_service.metrics_collector.get_metric_stats(
            'system_disk_usage_percent', start_time, end_time
        )
        
        return {
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            },
            'system_analytics': system_analytics,
            'active_alerts': active_alerts,
            'alert_count': len(active_alerts),
            'system_resources': {
                'cpu': cpu_stats,
                'memory': memory_stats,
                'disk': disk_stats
            },
            'thresholds': self.thresholds
        }
    
    async def get_agent_performance_report(
        self,
        agent_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get detailed performance report for a specific agent"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get agent analytics
        agent_analytics = await analytics_service.get_agent_analytics(
            agent_id, start_time, end_time
        )
        
        # Get agent-specific alerts
        agent_alerts = [
            {
                'alert_id': alert.alert_id,
                'severity': alert.severity.value,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat()
            }
            for alert in self.active_alerts.values()
            if agent_id in str(alert.details) and not alert.resolved
        ]
        
        return {
            'agent_id': agent_id,
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            },
            'analytics': agent_analytics,
            'alerts': agent_alerts,
            'performance_grade': self._calculate_performance_grade(agent_analytics)
        }
    
    def _calculate_performance_grade(self, analytics: Dict[str, Any]) -> str:
        """Calculate performance grade based on analytics"""
        success_rate = analytics.get('success_rate_percent', 0)
        avg_execution_time = analytics.get('execution_stats', {}).get('avg', 0)
        
        # Simple grading logic
        if success_rate >= 95 and avg_execution_time < 2000:
            return 'A'
        elif success_rate >= 90 and avg_execution_time < 5000:
            return 'B'
        elif success_rate >= 80 and avg_execution_time < 10000:
            return 'C'
        elif success_rate >= 70:
            return 'D'
        else:
            return 'F'

# Global performance monitor instance
performance_monitor = PerformanceMonitor()