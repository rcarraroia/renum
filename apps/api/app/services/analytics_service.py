"""
Analytics Service
Comprehensive analytics and monitoring system for integrations and agent executions
"""
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from datetime import datetime, timedelta
import asyncio
import json
import time
import logging
from collections import defaultdict, deque
import statistics
import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class MetricsCollector:
    """Real-time metrics collector with Redis backend"""
    
    def __init__(self):
        self.redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
        self.redis_client: Optional[redis.Redis] = None
        
        # In-memory fallback for when Redis is not available
        self.memory_metrics = defaultdict(deque)
        self.memory_counters = defaultdict(int)
        
        # Metric retention periods
        self.retention_periods = {
            'minute': 60,      # 1 minute
            'hour': 3600,      # 1 hour  
            'day': 86400,      # 1 day
            'week': 604800,    # 1 week
            'month': 2592000   # 30 days
        }
    
    async def get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with connection pooling"""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=20
                )
                await self.redis_client.ping()
                logger.info("Analytics Redis connection established")
            except Exception as e:
                logger.warning(f"Analytics Redis connection failed: {e}. Using in-memory fallback.")
                self.redis_client = None
        
        return self.redis_client
    
    async def record_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record a metric value with optional tags"""
        timestamp = timestamp or datetime.utcnow()
        tags = tags or {}
        
        # Create metric key
        tag_string = ",".join([f"{k}={v}" for k, v in sorted(tags.items())])
        metric_key = f"{metric_name}:{tag_string}" if tag_string else metric_name
        
        redis_client = await self.get_redis_client()
        
        if redis_client:
            try:
                # Store in Redis with timestamp
                await redis_client.zadd(
                    f"metrics:{metric_key}",
                    {json.dumps({'value': value, 'timestamp': timestamp.isoformat()}): timestamp.timestamp()}
                )
                
                # Set expiry for cleanup
                await redis_client.expire(f"metrics:{metric_key}", self.retention_periods['month'])
                
            except Exception as e:
                logger.error(f"Failed to record metric to Redis: {e}")
                # Fallback to memory
                self._record_metric_memory(metric_key, value, timestamp)
        else:
            # Use memory fallback
            self._record_metric_memory(metric_key, value, timestamp)
    
    def _record_metric_memory(self, metric_key: str, value: Union[int, float], timestamp: datetime) -> None:
        """Record metric in memory as fallback"""
        # Keep only recent metrics in memory (last hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        # Clean old metrics
        while (self.memory_metrics[metric_key] and 
               self.memory_metrics[metric_key][0]['timestamp'] < cutoff_time):
            self.memory_metrics[metric_key].popleft()
        
        # Add new metric
        self.memory_metrics[metric_key].append({
            'value': value,
            'timestamp': timestamp
        })
        
        # Limit memory usage
        if len(self.memory_metrics[metric_key]) > 1000:
            self.memory_metrics[metric_key].popleft()
    
    async def increment_counter(
        self,
        counter_name: str,
        increment: int = 1,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric"""
        tags = tags or {}
        tag_string = ",".join([f"{k}={v}" for k, v in sorted(tags.items())])
        counter_key = f"{counter_name}:{tag_string}" if tag_string else counter_name
        
        redis_client = await self.get_redis_client()
        
        if redis_client:
            try:
                await redis_client.incrby(f"counters:{counter_key}", increment)
                await redis_client.expire(f"counters:{counter_key}", self.retention_periods['month'])
            except Exception as e:
                logger.error(f"Failed to increment counter in Redis: {e}")
                self.memory_counters[counter_key] += increment
        else:
            self.memory_counters[counter_key] += increment
    
    async def get_metric_stats(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Get statistics for a metric over a time period"""
        tags = tags or {}
        tag_string = ",".join([f"{k}={v}" for k, v in sorted(tags.items())])
        metric_key = f"{metric_name}:{tag_string}" if tag_string else metric_name
        
        redis_client = await self.get_redis_client()
        
        if redis_client:
            try:
                # Get metrics from Redis
                results = await redis_client.zrangebyscore(
                    f"metrics:{metric_key}",
                    start_time.timestamp(),
                    end_time.timestamp(),
                    withscores=True
                )
                
                values = []
                for result, score in results:
                    data = json.loads(result)
                    values.append(data['value'])
                
            except Exception as e:
                logger.error(f"Failed to get metrics from Redis: {e}")
                values = self._get_metric_stats_memory(metric_key, start_time, end_time)
        else:
            values = self._get_metric_stats_memory(metric_key, start_time, end_time)
        
        if not values:
            return {
                'count': 0,
                'sum': 0,
                'avg': 0,
                'min': 0,
                'max': 0,
                'median': 0
            }
        
        return {
            'count': len(values),
            'sum': sum(values),
            'avg': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'median': statistics.median(values)
        }
    
    def _get_metric_stats_memory(self, metric_key: str, start_time: datetime, end_time: datetime) -> List[float]:
        """Get metric stats from memory"""
        values = []
        for metric in self.memory_metrics.get(metric_key, []):
            if start_time <= metric['timestamp'] <= end_time:
                values.append(metric['value'])
        return values
    
    async def get_counter_value(
        self,
        counter_name: str,
        tags: Optional[Dict[str, str]] = None
    ) -> int:
        """Get current counter value"""
        tags = tags or {}
        tag_string = ",".join([f"{k}={v}" for k, v in sorted(tags.items())])
        counter_key = f"{counter_name}:{tag_string}" if tag_string else counter_name
        
        redis_client = await self.get_redis_client()
        
        if redis_client:
            try:
                value = await redis_client.get(f"counters:{counter_key}")
                return int(value) if value else 0
            except Exception as e:
                logger.error(f"Failed to get counter from Redis: {e}")
                return self.memory_counters.get(counter_key, 0)
        else:
            return self.memory_counters.get(counter_key, 0)

class AnalyticsService:
    """Main analytics service for collecting and analyzing metrics"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        
        # Performance thresholds
        self.performance_thresholds = {
            'agent_execution_time_ms': 5000,  # 5 seconds
            'webhook_response_time_ms': 2000,  # 2 seconds
            'integration_error_rate': 0.05,   # 5%
            'api_response_time_ms': 1000       # 1 second
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            'error_rate_per_minute': 10,
            'failed_executions_per_hour': 50,
            'high_latency_requests_per_minute': 20
        }
    
    async def record_integration_metric(
        self,
        integration_id: UUID,
        metric_type: str,
        value: Union[int, float],
        additional_tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record integration-specific metric"""
        tags = {
            'integration_id': str(integration_id),
            'metric_type': metric_type
        }
        if additional_tags:
            tags.update(additional_tags)
        
        await self.metrics_collector.record_metric(
            'integration_metric',
            value,
            tags
        )
    
    async def record_webhook_processing(
        self,
        integration_id: UUID,
        provider: str,
        processing_time_ms: float,
        success: bool,
        payload_size: int
    ) -> None:
        """Record webhook processing metrics"""
        tags = {
            'integration_id': str(integration_id),
            'provider': provider,
            'success': str(success)
        }
        
        # Record processing time
        await self.metrics_collector.record_metric(
            'webhook_processing_time_ms',
            processing_time_ms,
            tags
        )
        
        # Record payload size
        await self.metrics_collector.record_metric(
            'webhook_payload_size_bytes',
            payload_size,
            tags
        )
        
        # Increment counters
        await self.metrics_collector.increment_counter(
            'webhook_processed_total',
            tags={'provider': provider}
        )
        
        if success:
            await self.metrics_collector.increment_counter(
                'webhook_processed_success',
                tags={'provider': provider}
            )
        else:
            await self.metrics_collector.increment_counter(
                'webhook_processed_error',
                tags={'provider': provider}
            )
        
        # Check for performance alerts
        if processing_time_ms > self.performance_thresholds['webhook_response_time_ms']:
            await self._trigger_performance_alert(
                'webhook_high_latency',
                {
                    'integration_id': str(integration_id),
                    'provider': provider,
                    'processing_time_ms': processing_time_ms
                }
            )
    
    async def record_agent_execution(
        self,
        agent_id: str,
        execution_id: UUID,
        execution_time_ms: float,
        success: bool,
        error_type: Optional[str] = None,
        cost_cents: Optional[float] = None
    ) -> None:
        """Record agent execution metrics"""
        tags = {
            'agent_id': agent_id,
            'success': str(success)
        }
        
        if error_type:
            tags['error_type'] = error_type
        
        # Record execution time
        await self.metrics_collector.record_metric(
            'agent_execution_time_ms',
            execution_time_ms,
            tags
        )
        
        # Record cost if provided
        if cost_cents is not None:
            await self.metrics_collector.record_metric(
                'agent_execution_cost_cents',
                cost_cents,
                {'agent_id': agent_id}
            )
        
        # Increment counters
        await self.metrics_collector.increment_counter(
            'agent_executions_total',
            tags={'agent_id': agent_id}
        )
        
        if success:
            await self.metrics_collector.increment_counter(
                'agent_executions_success',
                tags={'agent_id': agent_id}
            )
        else:
            await self.metrics_collector.increment_counter(
                'agent_executions_error',
                tags={'agent_id': agent_id, 'error_type': error_type or 'unknown'}
            )
        
        # Check for performance alerts
        if execution_time_ms > self.performance_thresholds['agent_execution_time_ms']:
            await self._trigger_performance_alert(
                'agent_high_latency',
                {
                    'agent_id': agent_id,
                    'execution_id': str(execution_id),
                    'execution_time_ms': execution_time_ms
                }
            )
    
    async def record_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[UUID] = None
    ) -> None:
        """Record API request metrics"""
        tags = {
            'endpoint': endpoint,
            'method': method,
            'status_code': str(status_code)
        }
        
        if user_id:
            tags['user_id'] = str(user_id)
        
        # Record response time
        await self.metrics_collector.record_metric(
            'api_response_time_ms',
            response_time_ms,
            tags
        )
        
        # Increment request counters
        await self.metrics_collector.increment_counter(
            'api_requests_total',
            tags={'endpoint': endpoint, 'method': method}
        )
        
        # Track errors
        if status_code >= 400:
            await self.metrics_collector.increment_counter(
                'api_requests_error',
                tags={'endpoint': endpoint, 'status_code': str(status_code)}
            )
        
        # Check for performance alerts
        if response_time_ms > self.performance_thresholds['api_response_time_ms']:
            await self._trigger_performance_alert(
                'api_high_latency',
                {
                    'endpoint': endpoint,
                    'method': method,
                    'response_time_ms': response_time_ms
                }
            )
    
    async def get_integration_analytics(
        self,
        integration_id: UUID,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get comprehensive analytics for an integration"""
        tags = {'integration_id': str(integration_id)}
        
        # Get webhook processing stats
        webhook_stats = await self.metrics_collector.get_metric_stats(
            'webhook_processing_time_ms',
            start_time,
            end_time,
            tags
        )
        
        # Get success/error counts
        success_count = await self.metrics_collector.get_counter_value(
            'webhook_processed_success',
            tags
        )
        
        error_count = await self.metrics_collector.get_counter_value(
            'webhook_processed_error',
            tags
        )
        
        total_count = success_count + error_count
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        return {
            'integration_id': str(integration_id),
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'webhook_processing': webhook_stats,
            'success_count': success_count,
            'error_count': error_count,
            'total_count': total_count,
            'success_rate_percent': round(success_rate, 2)
        }
    
    async def get_agent_analytics(
        self,
        agent_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get comprehensive analytics for an agent"""
        tags = {'agent_id': agent_id}
        
        # Get execution time stats
        execution_stats = await self.metrics_collector.get_metric_stats(
            'agent_execution_time_ms',
            start_time,
            end_time,
            tags
        )
        
        # Get cost stats
        cost_stats = await self.metrics_collector.get_metric_stats(
            'agent_execution_cost_cents',
            start_time,
            end_time,
            {'agent_id': agent_id}
        )
        
        # Get success/error counts
        success_count = await self.metrics_collector.get_counter_value(
            'agent_executions_success',
            tags
        )
        
        error_count = await self.metrics_collector.get_counter_value(
            'agent_executions_error',
            tags
        )
        
        total_count = success_count + error_count
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        return {
            'agent_id': agent_id,
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'execution_stats': execution_stats,
            'cost_stats': cost_stats,
            'success_count': success_count,
            'error_count': error_count,
            'total_count': total_count,
            'success_rate_percent': round(success_rate, 2)
        }
    
    async def get_system_analytics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get system-wide analytics"""
        # API request stats
        api_stats = await self.metrics_collector.get_metric_stats(
            'api_response_time_ms',
            start_time,
            end_time
        )
        
        # Total API requests
        total_requests = await self.metrics_collector.get_counter_value('api_requests_total')
        error_requests = await self.metrics_collector.get_counter_value('api_requests_error')
        
        # Agent execution stats
        total_executions = await self.metrics_collector.get_counter_value('agent_executions_total')
        successful_executions = await self.metrics_collector.get_counter_value('agent_executions_success')
        
        # Webhook processing stats
        total_webhooks = await self.metrics_collector.get_counter_value('webhook_processed_total')
        successful_webhooks = await self.metrics_collector.get_counter_value('webhook_processed_success')
        
        return {
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'api_requests': {
                'total': total_requests,
                'errors': error_requests,
                'error_rate_percent': round((error_requests / total_requests * 100) if total_requests > 0 else 0, 2),
                'response_time_stats': api_stats
            },
            'agent_executions': {
                'total': total_executions,
                'successful': successful_executions,
                'success_rate_percent': round((successful_executions / total_executions * 100) if total_executions > 0 else 0, 2)
            },
            'webhook_processing': {
                'total': total_webhooks,
                'successful': successful_webhooks,
                'success_rate_percent': round((successful_webhooks / total_webhooks * 100) if total_webhooks > 0 else 0, 2)
            }
        }
    
    async def _trigger_performance_alert(
        self,
        alert_type: str,
        details: Dict[str, Any]
    ) -> None:
        """Trigger performance alert"""
        alert_data = {
            'alert_type': alert_type,
            'timestamp': datetime.utcnow().isoformat(),
            'details': details,
            'severity': 'warning'
        }
        
        # Log alert
        logger.warning(f"Performance alert triggered: {json.dumps(alert_data)}")
        
        # Store alert for later retrieval
        await self.metrics_collector.record_metric(
            'performance_alert',
            1,
            {'alert_type': alert_type}
        )
    
    async def get_recent_alerts(
        self,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get recent performance alerts"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        end_time = datetime.utcnow()
        
        # This would typically query a dedicated alerts storage
        # For now, return mock data
        return [
            {
                'alert_type': 'webhook_high_latency',
                'timestamp': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                'details': {
                    'integration_id': 'test-integration',
                    'processing_time_ms': 3500
                },
                'severity': 'warning'
            }
        ]

# Global analytics service instance
analytics_service = AnalyticsService()