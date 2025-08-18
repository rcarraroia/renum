"""
Analytics API Endpoints
Comprehensive analytics and monitoring endpoints
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user, get_current_admin_user
from app.services.analytics_service import analytics_service
from app.services.performance_monitor import performance_monitor
from app.services.billing_service import billing_service, BillingTier
from app.services.alerting_service import alerting_service, AlertSeverity, AlertType

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Response Models
class AnalyticsResponse(BaseModel):
    """Base analytics response"""
    period: Dict[str, str]
    data: Dict[str, Any]

class IntegrationAnalyticsResponse(BaseModel):
    """Integration analytics response"""
    integration_id: str
    period: Dict[str, str]
    webhook_processing: Dict[str, Any]
    success_count: int
    error_count: int
    total_count: int
    success_rate_percent: float

class AgentAnalyticsResponse(BaseModel):
    """Agent analytics response"""
    agent_id: str
    period: Dict[str, str]
    execution_stats: Dict[str, Any]
    cost_stats: Dict[str, Any]
    success_count: int
    error_count: int
    total_count: int
    success_rate_percent: float

class SystemAnalyticsResponse(BaseModel):
    """System analytics response"""
    period: Dict[str, str]
    api_requests: Dict[str, Any]
    agent_executions: Dict[str, Any]
    webhook_processing: Dict[str, Any]

class PerformanceSummaryResponse(BaseModel):
    """Performance summary response"""
    period: Dict[str, str]
    system_analytics: Dict[str, Any]
    active_alerts: List[Dict[str, Any]]
    alert_count: int
    system_resources: Dict[str, Any]
    thresholds: Dict[str, Any]

class BillingSummaryResponse(BaseModel):
    """Billing summary response"""
    user_id: str
    billing_period: Dict[str, str]
    tier: str
    plan: Dict[str, Any]
    usage: Dict[str, Any]
    overages: Dict[str, Any]
    costs: Dict[str, Any]
    cost_breakdown: Dict[str, Any]

class AlertResponse(BaseModel):
    """Alert response"""
    alert_id: str
    rule_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    status: str
    created_at: str
    updated_at: str
    notification_count: int
    details: Dict[str, Any]

# Request Models
class CustomAlertRequest(BaseModel):
    """Custom alert creation request"""
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    severity: str = Field(..., regex="^(low|medium|high|critical)$")
    details: Optional[Dict[str, Any]] = None

class AlertActionRequest(BaseModel):
    """Alert action request"""
    note: Optional[str] = Field(None, max_length=500)

@router.get("/integrations/{integration_id}", response_model=IntegrationAnalyticsResponse)
async def get_integration_analytics(
    integration_id: UUID,
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze (max 7 days)"),
    current_user: Dict = Depends(get_current_user)
):
    """Get analytics for a specific integration"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        analytics = await analytics_service.get_integration_analytics(
            integration_id, start_time, end_time
        )
        
        return IntegrationAnalyticsResponse(**analytics)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get integration analytics: {str(e)}"
        )

@router.get("/agents/{agent_id}", response_model=AgentAnalyticsResponse)
async def get_agent_analytics(
    agent_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze (max 7 days)"),
    current_user: Dict = Depends(get_current_user)
):
    """Get analytics for a specific agent"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        analytics = await analytics_service.get_agent_analytics(
            agent_id, start_time, end_time
        )
        
        return AgentAnalyticsResponse(**analytics)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent analytics: {str(e)}"
        )

@router.get("/system", response_model=SystemAnalyticsResponse)
async def get_system_analytics(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze (max 7 days)"),
    current_user: Dict = Depends(get_current_admin_user)
):
    """Get system-wide analytics (admin only)"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        analytics = await analytics_service.get_system_analytics(start_time, end_time)
        
        return SystemAnalyticsResponse(**analytics)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system analytics: {str(e)}"
        )

@router.get("/performance/summary", response_model=PerformanceSummaryResponse)
async def get_performance_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze (max 7 days)"),
    current_user: Dict = Depends(get_current_admin_user)
):
    """Get performance summary (admin only)"""
    try:
        summary = await performance_monitor.get_performance_summary(hours)
        return PerformanceSummaryResponse(**summary)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance summary: {str(e)}"
        )

@router.get("/performance/agents/{agent_id}")
async def get_agent_performance_report(
    agent_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze (max 7 days)"),
    current_user: Dict = Depends(get_current_user)
):
    """Get detailed performance report for an agent"""
    try:
        report = await performance_monitor.get_agent_performance_report(agent_id, hours)
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent performance report: {str(e)}"
        )

@router.get("/billing/summary", response_model=BillingSummaryResponse)
async def get_billing_summary(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    tier: str = Query("free", regex="^(free|starter|professional|enterprise)$"),
    current_user: Dict = Depends(get_current_user)
):
    """Get billing summary for current user"""
    try:
        user_id = UUID(current_user['user_id'])
        
        # Default to current month if dates not provided
        if not start_date:
            now = datetime.utcnow()
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if not end_date:
            end_date = datetime.utcnow()
        
        billing_tier = BillingTier(tier)
        
        summary = await billing_service.get_user_billing_summary(
            user_id, start_date, end_date, billing_tier
        )
        
        return BillingSummaryResponse(**summary)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get billing summary: {str(e)}"
        )

@router.get("/billing/estimate")
async def estimate_monthly_cost(
    tier: str = Query(..., regex="^(free|starter|professional|enterprise)$"),
    projected_executions: int = Query(..., ge=0, description="Projected monthly executions"),
    projected_api_requests: int = Query(..., ge=0, description="Projected monthly API requests"),
    current_user: Dict = Depends(get_current_user)
):
    """Estimate monthly cost based on projected usage"""
    try:
        user_id = UUID(current_user['user_id'])
        billing_tier = BillingTier(tier)
        
        estimate = await billing_service.estimate_monthly_cost(
            user_id, billing_tier, projected_executions, projected_api_requests
        )
        
        return estimate
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to estimate cost: {str(e)}"
        )

@router.get("/billing/cost-analytics")
async def get_cost_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    group_by: str = Query("day", regex="^(hour|day|week|month)$"),
    current_user: Dict = Depends(get_current_admin_user)
):
    """Get system-wide cost analytics (admin only)"""
    try:
        # Default to last 30 days if dates not provided
        if not end_date:
            end_date = datetime.utcnow()
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        analytics = await billing_service.get_cost_analytics(start_date, end_date, group_by)
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost analytics: {str(e)}"
        )

@router.get("/alerts", response_model=List[AlertResponse])
async def get_active_alerts(
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    alert_type: Optional[str] = Query(None, regex="^(performance|error_rate|cost_threshold|system_resource|integration_failure|security|custom)$"),
    current_user: Dict = Depends(get_current_user)
):
    """Get active alerts"""
    try:
        severity_filter = AlertSeverity(severity) if severity else None
        type_filter = AlertType(alert_type) if alert_type else None
        
        alerts = await alerting_service.get_active_alerts(severity_filter, type_filter)
        
        return [AlertResponse(**alert) for alert in alerts]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )

@router.get("/alerts/statistics")
async def get_alert_statistics(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze (max 7 days)"),
    current_user: Dict = Depends(get_current_user)
):
    """Get alert statistics"""
    try:
        stats = await alerting_service.get_alert_statistics(hours)
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert statistics: {str(e)}"
        )

@router.post("/alerts/custom")
async def create_custom_alert(
    alert_request: CustomAlertRequest,
    current_user: Dict = Depends(get_current_admin_user)
):
    """Create a custom alert (admin only)"""
    try:
        severity = AlertSeverity(alert_request.severity)
        
        alert_id = await alerting_service.create_custom_alert(
            title=alert_request.title,
            message=alert_request.message,
            severity=severity,
            details=alert_request.details
        )
        
        return {"alert_id": alert_id, "message": "Custom alert created successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create custom alert: {str(e)}"
        )

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    action_request: AlertActionRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Acknowledge an alert"""
    try:
        user_id = UUID(current_user['user_id'])
        
        success = await alerting_service.acknowledge_alert(
            alert_id, user_id, action_request.note
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found or already acknowledged"
            )
        
        return {"message": "Alert acknowledged successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    action_request: AlertActionRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Resolve an alert"""
    try:
        user_id = UUID(current_user['user_id'])
        
        success = await alerting_service.resolve_alert(
            alert_id, user_id, action_request.note
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        return {"message": "Alert resolved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}"
        )

@router.get("/metrics/export")
async def export_metrics(
    format: str = Query("json", regex="^(json|csv)$"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    current_user: Dict = Depends(get_current_admin_user)
):
    """Export metrics data (admin only)"""
    try:
        # Default to last 7 days if dates not provided
        if not end_date:
            end_date = datetime.utcnow()
        
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        metrics_data = await analytics_service.metrics_collector.export_metrics(
            format, start_date.isoformat(), end_date.isoformat()
        )
        
        if format == "csv":
            from fastapi.responses import Response
            return Response(
                content=metrics_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=metrics.csv"}
            )
        else:
            return metrics_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export metrics: {str(e)}"
        )

@router.get("/dashboard")
async def get_dashboard_data(
    current_user: Dict = Depends(get_current_user)
):
    """Get dashboard data for current user"""
    try:
        user_id = UUID(current_user['user_id'])
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        # Get user's recent activity
        # This would typically query user-specific data
        # For now, return mock dashboard data
        
        dashboard_data = {
            'user_id': str(user_id),
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'summary': {
                'total_executions': 45,
                'successful_executions': 42,
                'failed_executions': 3,
                'success_rate_percent': 93.3,
                'total_cost_cents': 127,
                'active_integrations': 3,
                'active_alerts': 1
            },
            'recent_executions': [
                {
                    'agent_id': 'sa-whatsapp',
                    'execution_time_ms': 1250,
                    'success': True,
                    'cost_cents': 2,
                    'timestamp': (end_time - timedelta(minutes=15)).isoformat()
                },
                {
                    'agent_id': 'sa-gmail',
                    'execution_time_ms': 2100,
                    'success': True,
                    'cost_cents': 3,
                    'timestamp': (end_time - timedelta(minutes=30)).isoformat()
                }
            ],
            'cost_trend': [
                {'date': (end_time - timedelta(days=6)).strftime('%Y-%m-%d'), 'cost_cents': 89},
                {'date': (end_time - timedelta(days=5)).strftime('%Y-%m-%d'), 'cost_cents': 95},
                {'date': (end_time - timedelta(days=4)).strftime('%Y-%m-%d'), 'cost_cents': 102},
                {'date': (end_time - timedelta(days=3)).strftime('%Y-%m-%d'), 'cost_cents': 87},
                {'date': (end_time - timedelta(days=2)).strftime('%Y-%m-%d'), 'cost_cents': 134},
                {'date': (end_time - timedelta(days=1)).strftime('%Y-%m-%d'), 'cost_cents': 156},
                {'date': end_time.strftime('%Y-%m-%d'), 'cost_cents': 127}
            ]
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {str(e)}"
        )