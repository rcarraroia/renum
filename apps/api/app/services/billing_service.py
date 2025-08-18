"""
Billing and Cost Tracking Service
Comprehensive cost tracking and billing analytics for agent executions and API usage
"""
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import logging
from dataclasses import dataclass

from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class BillingTier(Enum):
    """User billing tiers"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class CostType(Enum):
    """Types of costs"""
    AGENT_EXECUTION = "agent_execution"
    API_REQUEST = "api_request"
    WEBHOOK_PROCESSING = "webhook_processing"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"

@dataclass
class CostItem:
    """Individual cost item"""
    cost_id: str
    user_id: UUID
    cost_type: CostType
    amount_cents: int
    currency: str
    description: str
    metadata: Dict[str, Any]
    timestamp: datetime

@dataclass
class BillingPlan:
    """Billing plan configuration"""
    tier: BillingTier
    monthly_fee_cents: int
    included_executions: int
    included_api_requests: int
    included_storage_gb: int
    overage_rates: Dict[str, int]  # Cost per unit in cents

class BillingService:
    """Service for cost tracking and billing analytics"""
    
    def __init__(self):
        # Billing plans configuration
        self.billing_plans = {
            BillingTier.FREE: BillingPlan(
                tier=BillingTier.FREE,
                monthly_fee_cents=0,
                included_executions=100,
                included_api_requests=1000,
                included_storage_gb=1,
                overage_rates={
                    'execution': 5,      # 5 cents per execution
                    'api_request': 1,    # 1 cent per 10 requests
                    'storage_gb': 50     # 50 cents per GB
                }
            ),
            BillingTier.STARTER: BillingPlan(
                tier=BillingTier.STARTER,
                monthly_fee_cents=2900,  # $29
                included_executions=1000,
                included_api_requests=10000,
                included_storage_gb=10,
                overage_rates={
                    'execution': 3,      # 3 cents per execution
                    'api_request': 1,    # 1 cent per 20 requests
                    'storage_gb': 40     # 40 cents per GB
                }
            ),
            BillingTier.PROFESSIONAL: BillingPlan(
                tier=BillingTier.PROFESSIONAL,
                monthly_fee_cents=9900,  # $99
                included_executions=5000,
                included_api_requests=50000,
                included_storage_gb=50,
                overage_rates={
                    'execution': 2,      # 2 cents per execution
                    'api_request': 1,    # 1 cent per 50 requests
                    'storage_gb': 30     # 30 cents per GB
                }
            ),
            BillingTier.ENTERPRISE: BillingPlan(
                tier=BillingTier.ENTERPRISE,
                monthly_fee_cents=29900,  # $299
                included_executions=25000,
                included_api_requests=250000,
                included_storage_gb=250,
                overage_rates={
                    'execution': 1,      # 1 cent per execution
                    'api_request': 1,    # 1 cent per 100 requests
                    'storage_gb': 20     # 20 cents per GB
                }
            )
        }
        
        # Agent execution costs (in cents)
        self.agent_costs = {
            'sa-gmail': 2,        # 2 cents per execution
            'sa-whatsapp': 1,     # 1 cent per execution
            'sa-telegram': 1,     # 1 cent per execution
            'sa-supabase': 1,     # 1 cent per execution
            'sa-http-generic': 1, # 1 cent per execution
        }
        
        # API endpoint costs (in cents per request)
        self.api_costs = {
            '/api/v1/orchestrator/execute': 5,  # 5 cents per orchestration
            '/api/v1/agents/execute': 2,        # 2 cents per agent execution
            '/api/v1/webhooks/': 1,             # 1 cent per webhook
            'default': 0                        # Free for other endpoints
        }
    
    async def record_agent_execution_cost(
        self,
        user_id: UUID,
        agent_id: str,
        execution_id: UUID,
        success: bool,
        execution_time_ms: float,
        additional_costs: Optional[Dict[str, int]] = None
    ) -> int:
        """Record cost for agent execution"""
        # Base cost for agent execution
        base_cost = self.agent_costs.get(agent_id, 1)  # Default 1 cent
        
        # Calculate time-based cost (longer executions cost more)
        time_multiplier = 1.0
        if execution_time_ms > 10000:  # > 10 seconds
            time_multiplier = 1.5
        elif execution_time_ms > 30000:  # > 30 seconds
            time_multiplier = 2.0
        
        # Failed executions cost 50% of successful ones
        success_multiplier = 1.0 if success else 0.5
        
        # Calculate total cost
        total_cost_cents = int(base_cost * time_multiplier * success_multiplier)
        
        # Add additional costs if provided
        if additional_costs:
            total_cost_cents += sum(additional_costs.values())
        
        # Record cost item
        cost_item = CostItem(
            cost_id=f"exec_{execution_id}",
            user_id=user_id,
            cost_type=CostType.AGENT_EXECUTION,
            amount_cents=total_cost_cents,
            currency="USD",
            description=f"Agent {agent_id} execution",
            metadata={
                'agent_id': agent_id,
                'execution_id': str(execution_id),
                'execution_time_ms': execution_time_ms,
                'success': success,
                'base_cost': base_cost,
                'time_multiplier': time_multiplier,
                'success_multiplier': success_multiplier,
                'additional_costs': additional_costs or {}
            },
            timestamp=datetime.utcnow()
        )
        
        await self._store_cost_item(cost_item)
        
        # Record in analytics
        await analytics_service.record_agent_execution(
            agent_id=agent_id,
            execution_id=execution_id,
            execution_time_ms=execution_time_ms,
            success=success,
            cost_cents=float(total_cost_cents)
        )
        
        return total_cost_cents
    
    async def record_api_request_cost(
        self,
        user_id: UUID,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int
    ) -> int:
        """Record cost for API request"""
        # Get base cost for endpoint
        base_cost = self.api_costs.get(endpoint, self.api_costs['default'])
        
        # No cost for failed requests (4xx, 5xx)
        if status_code >= 400:
            base_cost = 0
        
        # High latency requests cost more
        latency_multiplier = 1.0
        if response_time_ms > 5000:  # > 5 seconds
            latency_multiplier = 1.5
        
        total_cost_cents = int(base_cost * latency_multiplier)
        
        if total_cost_cents > 0:
            cost_item = CostItem(
                cost_id=f"api_{int(datetime.utcnow().timestamp() * 1000000)}",
                user_id=user_id,
                cost_type=CostType.API_REQUEST,
                amount_cents=total_cost_cents,
                currency="USD",
                description=f"API request {method} {endpoint}",
                metadata={
                    'endpoint': endpoint,
                    'method': method,
                    'response_time_ms': response_time_ms,
                    'status_code': status_code,
                    'base_cost': base_cost,
                    'latency_multiplier': latency_multiplier
                },
                timestamp=datetime.utcnow()
            )
            
            await self._store_cost_item(cost_item)
        
        return total_cost_cents
    
    async def record_webhook_processing_cost(
        self,
        user_id: UUID,
        integration_id: UUID,
        provider: str,
        processing_time_ms: float,
        payload_size_bytes: int,
        success: bool
    ) -> int:
        """Record cost for webhook processing"""
        # Base cost per webhook
        base_cost = 1  # 1 cent per webhook
        
        # Size-based cost (large payloads cost more)
        size_multiplier = 1.0
        if payload_size_bytes > 1024 * 1024:  # > 1MB
            size_multiplier = 2.0
        elif payload_size_bytes > 100 * 1024:  # > 100KB
            size_multiplier = 1.5
        
        # Processing time multiplier
        time_multiplier = 1.0
        if processing_time_ms > 5000:  # > 5 seconds
            time_multiplier = 1.5
        
        # Failed processing costs 25% of successful
        success_multiplier = 1.0 if success else 0.25
        
        total_cost_cents = int(base_cost * size_multiplier * time_multiplier * success_multiplier)
        
        cost_item = CostItem(
            cost_id=f"webhook_{int(datetime.utcnow().timestamp() * 1000000)}",
            user_id=user_id,
            cost_type=CostType.WEBHOOK_PROCESSING,
            amount_cents=total_cost_cents,
            currency="USD",
            description=f"Webhook processing for {provider}",
            metadata={
                'integration_id': str(integration_id),
                'provider': provider,
                'processing_time_ms': processing_time_ms,
                'payload_size_bytes': payload_size_bytes,
                'success': success,
                'base_cost': base_cost,
                'size_multiplier': size_multiplier,
                'time_multiplier': time_multiplier,
                'success_multiplier': success_multiplier
            },
            timestamp=datetime.utcnow()
        )
        
        await self._store_cost_item(cost_item)
        
        return total_cost_cents
    
    async def _store_cost_item(self, cost_item: CostItem) -> None:
        """Store cost item in analytics system"""
        try:
            # Record cost metric
            await analytics_service.metrics_collector.record_metric(
                'billing_cost_cents',
                cost_item.amount_cents,
                {
                    'user_id': str(cost_item.user_id),
                    'cost_type': cost_item.cost_type.value,
                    'currency': cost_item.currency
                }
            )
            
            # Increment cost counter
            await analytics_service.metrics_collector.increment_counter(
                'billing_items_total',
                tags={
                    'user_id': str(cost_item.user_id),
                    'cost_type': cost_item.cost_type.value
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to store cost item: {e}")
    
    async def get_user_billing_summary(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        tier: BillingTier = BillingTier.FREE
    ) -> Dict[str, Any]:
        """Get comprehensive billing summary for user"""
        # Get cost metrics for the period
        cost_stats = await analytics_service.metrics_collector.get_metric_stats(
            'billing_cost_cents',
            start_date,
            end_date,
            {'user_id': str(user_id)}
        )
        
        # Get usage counts
        execution_count = await analytics_service.metrics_collector.get_counter_value(
            'agent_executions_total',
            {'user_id': str(user_id)}
        )
        
        api_request_count = await analytics_service.metrics_collector.get_counter_value(
            'api_requests_total',
            {'user_id': str(user_id)}
        )
        
        webhook_count = await analytics_service.metrics_collector.get_counter_value(
            'webhook_processed_total',
            {'user_id': str(user_id)}
        )
        
        # Get billing plan
        plan = self.billing_plans[tier]
        
        # Calculate overages
        execution_overage = max(0, execution_count - plan.included_executions)
        api_overage = max(0, api_request_count - plan.included_api_requests)
        
        # Calculate overage costs
        execution_overage_cost = execution_overage * plan.overage_rates['execution']
        api_overage_cost = (api_overage // 10) * plan.overage_rates['api_request']  # Per 10 requests
        
        total_overage_cost = execution_overage_cost + api_overage_cost
        total_cost = plan.monthly_fee_cents + total_overage_cost
        
        return {
            'user_id': str(user_id),
            'billing_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'tier': tier.value,
            'plan': {
                'monthly_fee_cents': plan.monthly_fee_cents,
                'included_executions': plan.included_executions,
                'included_api_requests': plan.included_api_requests,
                'included_storage_gb': plan.included_storage_gb
            },
            'usage': {
                'executions': execution_count,
                'api_requests': api_request_count,
                'webhooks': webhook_count
            },
            'overages': {
                'executions': execution_overage,
                'api_requests': api_overage,
                'execution_overage_cost_cents': execution_overage_cost,
                'api_overage_cost_cents': api_overage_cost
            },
            'costs': {
                'monthly_fee_cents': plan.monthly_fee_cents,
                'overage_costs_cents': total_overage_cost,
                'total_cost_cents': total_cost,
                'recorded_costs_cents': int(cost_stats['sum']) if cost_stats['count'] > 0 else 0
            },
            'cost_breakdown': await self._get_cost_breakdown(user_id, start_date, end_date)
        }
    
    async def _get_cost_breakdown(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get detailed cost breakdown by type"""
        breakdown = {}
        
        for cost_type in CostType:
            cost_stats = await analytics_service.metrics_collector.get_metric_stats(
                'billing_cost_cents',
                start_date,
                end_date,
                {
                    'user_id': str(user_id),
                    'cost_type': cost_type.value
                }
            )
            
            breakdown[cost_type.value] = {
                'total_cost_cents': int(cost_stats['sum']) if cost_stats['count'] > 0 else 0,
                'item_count': cost_stats['count'],
                'avg_cost_cents': round(cost_stats['avg'], 2) if cost_stats['count'] > 0 else 0
            }
        
        return breakdown
    
    async def get_cost_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = 'day'
    ) -> Dict[str, Any]:
        """Get system-wide cost analytics"""
        # This would typically aggregate costs across all users
        # For now, return summary statistics
        
        total_cost_stats = await analytics_service.metrics_collector.get_metric_stats(
            'billing_cost_cents',
            start_date,
            end_date
        )
        
        total_items = await analytics_service.metrics_collector.get_counter_value(
            'billing_items_total'
        )
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_revenue_cents': int(total_cost_stats['sum']) if total_cost_stats['count'] > 0 else 0,
            'total_billing_items': total_items,
            'avg_cost_per_item_cents': round(total_cost_stats['avg'], 2) if total_cost_stats['count'] > 0 else 0,
            'cost_distribution': {
                'min_cents': int(total_cost_stats['min']) if total_cost_stats['count'] > 0 else 0,
                'max_cents': int(total_cost_stats['max']) if total_cost_stats['count'] > 0 else 0,
                'median_cents': int(total_cost_stats['median']) if total_cost_stats['count'] > 0 else 0
            }
        }
    
    async def estimate_monthly_cost(
        self,
        user_id: UUID,
        tier: BillingTier,
        projected_executions: int,
        projected_api_requests: int
    ) -> Dict[str, Any]:
        """Estimate monthly cost based on projected usage"""
        plan = self.billing_plans[tier]
        
        # Calculate projected overages
        execution_overage = max(0, projected_executions - plan.included_executions)
        api_overage = max(0, projected_api_requests - plan.included_api_requests)
        
        # Calculate overage costs
        execution_overage_cost = execution_overage * plan.overage_rates['execution']
        api_overage_cost = (api_overage // 10) * plan.overage_rates['api_request']
        
        total_overage_cost = execution_overage_cost + api_overage_cost
        total_estimated_cost = plan.monthly_fee_cents + total_overage_cost
        
        return {
            'user_id': str(user_id),
            'tier': tier.value,
            'projected_usage': {
                'executions': projected_executions,
                'api_requests': projected_api_requests
            },
            'plan_limits': {
                'included_executions': plan.included_executions,
                'included_api_requests': plan.included_api_requests
            },
            'projected_overages': {
                'executions': execution_overage,
                'api_requests': api_overage
            },
            'estimated_costs': {
                'monthly_fee_cents': plan.monthly_fee_cents,
                'execution_overage_cents': execution_overage_cost,
                'api_overage_cents': api_overage_cost,
                'total_overage_cents': total_overage_cost,
                'total_estimated_cents': total_estimated_cost
            },
            'cost_savings_by_tier': await self._calculate_tier_comparison(
                projected_executions, projected_api_requests
            )
        }
    
    async def _calculate_tier_comparison(
        self,
        executions: int,
        api_requests: int
    ) -> Dict[str, int]:
        """Calculate costs across all tiers for comparison"""
        comparison = {}
        
        for tier in BillingTier:
            plan = self.billing_plans[tier]
            
            execution_overage = max(0, executions - plan.included_executions)
            api_overage = max(0, api_requests - plan.included_api_requests)
            
            execution_overage_cost = execution_overage * plan.overage_rates['execution']
            api_overage_cost = (api_overage // 10) * plan.overage_rates['api_request']
            
            total_cost = plan.monthly_fee_cents + execution_overage_cost + api_overage_cost
            comparison[tier.value] = total_cost
        
        return comparison

# Global billing service instance
billing_service = BillingService()