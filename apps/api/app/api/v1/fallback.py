"""
Fallback API Endpoints
API endpoints for handling unsupported integrations and suggestions
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user, get_current_admin_user
from app.services.fallback_service import fallback_service, IntegrationCategory
from app.services.suggestion_engine import suggestion_engine, MatchingStrategy

router = APIRouter(prefix="/fallback", tags=["Fallback System"])

# Request Models
class UnsupportedIntegrationRequest(BaseModel):
    """Request for unsupported integration handling"""
    integration_name: str = Field(..., min_length=1, max_length=100)
    context: Optional[Dict[str, Any]] = None

class IntegrationRequestCreate(BaseModel):
    """Create integration request"""
    integration_name: str = Field(..., min_length=1, max_length=100)
    integration_url: Optional[str] = Field(None, max_length=500)
    description: str = Field(..., min_length=10, max_length=1000)
    use_case: str = Field(..., min_length=10, max_length=500)
    priority: str = Field("medium", regex="^(low|medium|high|critical)$")
    business_impact: str = Field("", max_length=500)
    expected_volume: int = Field(100, ge=1, le=1000000)

class SuggestionRequest(BaseModel):
    """Request for integration suggestions"""
    target_integration: str = Field(..., min_length=1, max_length=100)
    required_capabilities: List[str] = Field(default_factory=list)
    use_case: Optional[str] = Field(None, max_length=500)
    user_context: Optional[Dict[str, Any]] = None
    strategy: str = Field("hybrid", regex="^(exact_match|semantic_similarity|capability_based|use_case_based|hybrid)$")

class VoteRequest(BaseModel):
    """Vote for integration request"""
    request_id: str = Field(..., min_length=1)

# Response Models
class UnsupportedIntegrationResponse(BaseModel):
    """Response for unsupported integration"""
    integration_name: str
    supported: bool
    analysis: Dict[str, Any]
    suggestions: List[Dict[str, Any]]
    can_use_generic_http: bool
    third_party_options: List[Dict[str, Any]]
    request_integration_url: str
    estimated_development_time: str

class IntegrationRequestResponse(BaseModel):
    """Integration request response"""
    request_id: str
    integration_name: str
    integration_url: Optional[str]
    category: str
    description: str
    use_case: str
    priority: str
    business_impact: str
    expected_volume: int
    votes: int
    status: str
    requested_at: str
    comments_count: int

class SuggestionResponse(BaseModel):
    """Integration suggestion response"""
    suggestion_id: str
    suggestion_type: str
    title: str
    description: str
    confidence_score: float
    implementation_effort: str
    available_now: bool
    details: Dict[str, Any]
    alternatives: List[str]

class IntegrationMatchResponse(BaseModel):
    """Integration match response"""
    integration_id: str
    integration_name: str
    match_score: float
    capability_matches: List[Dict[str, Any]]
    pros: List[str]
    cons: List[str]
    setup_complexity: str
    estimated_setup_time: str
    cost_comparison: Dict[str, Any]

class RoadmapResponse(BaseModel):
    """Integration roadmap response"""
    total_requests: int
    by_status: Dict[str, int]
    top_requested: List[Dict[str, Any]]
    development_priorities: List[Dict[str, Any]]
    estimated_completion: Dict[str, Any]

@router.post("/unsupported", response_model=UnsupportedIntegrationResponse)
async def handle_unsupported_integration(
    request: UnsupportedIntegrationRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Handle request for unsupported integration"""
    try:
        user_id = UUID(current_user['user_id'])
        
        result = await fallback_service.handle_unsupported_integration(
            integration_name=request.integration_name,
            user_id=user_id,
            context=request.context
        )
        
        return UnsupportedIntegrationResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle unsupported integration: {str(e)}"
        )

@router.post("/suggestions", response_model=List[IntegrationMatchResponse])
async def get_integration_suggestions(
    request: SuggestionRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Get intelligent integration suggestions"""
    try:
        strategy = MatchingStrategy(request.strategy)
        
        matches = await suggestion_engine.suggest_alternatives(
            target_integration=request.target_integration,
            required_capabilities=request.required_capabilities,
            use_case=request.use_case,
            user_context=request.user_context,
            strategy=strategy
        )
        
        return [
            IntegrationMatchResponse(
                integration_id=match.integration_id,
                integration_name=match.integration_name,
                match_score=match.match_score,
                capability_matches=[
                    {
                        'capability_name': cm.capability_name,
                        'match_score': cm.match_score,
                        'match_type': cm.match_type,
                        'explanation': cm.explanation
                    } for cm in match.capability_matches
                ],
                pros=match.pros,
                cons=match.cons,
                setup_complexity=match.setup_complexity,
                estimated_setup_time=match.estimated_setup_time,
                cost_comparison=match.cost_comparison
            ) for match in matches
        ]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )

@router.post("/requests", response_model=Dict[str, str])
async def create_integration_request(
    request: IntegrationRequestCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create a formal integration request"""
    try:
        user_id = UUID(current_user['user_id'])
        
        request_id = await fallback_service.create_integration_request(
            user_id=user_id,
            integration_name=request.integration_name,
            description=request.description,
            use_case=request.use_case,
            priority=request.priority,
            integration_url=request.integration_url,
            business_impact=request.business_impact,
            expected_volume=request.expected_volume
        )
        
        return {
            "request_id": request_id,
            "message": "Integration request created successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create integration request: {str(e)}"
        )

@router.get("/requests", response_model=List[IntegrationRequestResponse])
async def list_integration_requests(
    status_filter: Optional[str] = Query(None, regex="^(pending|in_review|approved|rejected|implemented)$"),
    category: Optional[str] = Query(None, regex="^(communication|database|messaging|storage|analytics|crm|ecommerce|social_media|productivity|automation|payment|marketing|other)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_user)
):
    """List integration requests with filtering"""
    try:
        category_filter = IntegrationCategory(category) if category else None
        
        requests = await fallback_service.get_integration_requests(
            status=status_filter,
            category=category_filter,
            limit=limit,
            offset=offset
        )
        
        return [IntegrationRequestResponse(**req) for req in requests]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list integration requests: {str(e)}"
        )

@router.post("/requests/{request_id}/vote")
async def vote_for_integration_request(
    request_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Vote for an integration request"""
    try:
        user_id = UUID(current_user['user_id'])
        
        success = await fallback_service.vote_for_integration_request(request_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration request not found"
            )
        
        return {"message": "Vote recorded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to vote for integration request: {str(e)}"
        )

@router.get("/roadmap", response_model=RoadmapResponse)
async def get_integration_roadmap(
    current_user: Dict = Depends(get_current_user)
):
    """Get integration development roadmap"""
    try:
        roadmap = await fallback_service.get_integration_roadmap()
        return RoadmapResponse(**roadmap)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get integration roadmap: {str(e)}"
        )

@router.get("/capabilities")
async def get_supported_capabilities(
    current_user: Dict = Depends(get_current_user)
):
    """Get list of supported capabilities"""
    try:
        capabilities = {}
        
        # Get capabilities from suggestion engine
        for category, caps in suggestion_engine.capability_taxonomy.items():
            capabilities[category] = {}
            for cap_name, cap_info in caps.items():
                capabilities[category][cap_name] = {
                    'aliases': cap_info.get('aliases', []),
                    'related': cap_info.get('related', []),
                    'parameters': cap_info.get('parameters', [])
                }
        
        return {
            'capabilities': capabilities,
            'total_categories': len(capabilities),
            'total_capabilities': sum(len(caps) for caps in capabilities.values())
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get capabilities: {str(e)}"
        )

@router.get("/third-party-connectors")
async def get_third_party_connectors(
    current_user: Dict = Depends(get_current_user)
):
    """Get available third-party connectors"""
    try:
        connectors = fallback_service.third_party_connectors
        
        return {
            'connectors': [
                {
                    'connector_id': connector_id,
                    'name': info['name'],
                    'description': info['description'],
                    'supported_apps': info.get('supported_apps', []),
                    'pricing': info.get('pricing', 'unknown'),
                    'setup_complexity': info.get('setup_complexity', 'medium'),
                    'webhook_url': info.get('webhook_url', 'configurable')
                }
                for connector_id, info in connectors.items()
            ],
            'total_connectors': len(connectors)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get third-party connectors: {str(e)}"
        )

@router.get("/integration-patterns")
async def get_integration_patterns(
    current_user: Dict = Depends(get_current_user)
):
    """Get common integration patterns"""
    try:
        patterns = fallback_service.integration_patterns
        
        return {
            'patterns': [
                {
                    'pattern_name': pattern_name,
                    'keywords': info['keywords'],
                    'category': info['category'].value,
                    'similar_to': info['similar_to'],
                    'common_endpoints': info['common_endpoints']
                }
                for pattern_name, info in patterns.items()
            ],
            'total_patterns': len(patterns)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get integration patterns: {str(e)}"
        )

@router.get("/stats")
async def get_fallback_stats(
    current_user: Dict = Depends(get_current_admin_user)
):
    """Get fallback system statistics (admin only)"""
    try:
        # Get basic stats
        total_requests = len(fallback_service.integration_requests)
        
        # Group by status
        by_status = {}
        by_category = {}
        by_priority = {}
        
        for request in fallback_service.integration_requests.values():
            # By status
            status = request.status
            by_status[status] = by_status.get(status, 0) + 1
            
            # By category
            category = request.category.value
            by_category[category] = by_category.get(category, 0) + 1
            
            # By priority
            priority = request.priority
            by_priority[priority] = by_priority.get(priority, 0) + 1
        
        # Get top voted requests
        top_voted = sorted(
            fallback_service.integration_requests.values(),
            key=lambda x: x.votes,
            reverse=True
        )[:10]
        
        return {
            'total_requests': total_requests,
            'by_status': by_status,
            'by_category': by_category,
            'by_priority': by_priority,
            'top_voted': [
                {
                    'integration_name': req.integration_name,
                    'votes': req.votes,
                    'category': req.category.value,
                    'priority': req.priority,
                    'status': req.status
                } for req in top_voted
            ],
            'supported_integrations': len(fallback_service.supported_integrations),
            'third_party_connectors': len(fallback_service.third_party_connectors),
            'integration_patterns': len(fallback_service.integration_patterns)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get fallback stats: {str(e)}"
        )