"""
Fallback Service
Intelligent response system for unsupported integrations and tools
"""
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import re
from dataclasses import dataclass

from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class IntegrationCategory(Enum):
    """Categories of integrations"""
    COMMUNICATION = "communication"
    DATABASE = "database"
    MESSAGING = "messaging"
    STORAGE = "storage"
    ANALYTICS = "analytics"
    CRM = "crm"
    ECOMMERCE = "ecommerce"
    SOCIAL_MEDIA = "social_media"
    PRODUCTIVITY = "productivity"
    AUTOMATION = "automation"
    PAYMENT = "payment"
    MARKETING = "marketing"
    OTHER = "other"

class SuggestionType(Enum):
    """Types of suggestions"""
    DIRECT_ALTERNATIVE = "direct_alternative"
    SIMILAR_CAPABILITY = "similar_capability"
    GENERIC_HTTP = "generic_http"
    THIRD_PARTY_CONNECTOR = "third_party_connector"
    CUSTOM_DEVELOPMENT = "custom_development"

@dataclass
class IntegrationCapability:
    """Represents a capability of an integration"""
    name: str
    description: str
    category: IntegrationCategory
    required_auth: List[str]  # e.g., ["api_key", "oauth2"]
    endpoints: List[str]
    data_formats: List[str]  # e.g., ["json", "xml", "csv"]

@dataclass
class IntegrationSuggestion:
    """Suggestion for unsupported integration"""
    suggestion_id: str
    suggestion_type: SuggestionType
    title: str
    description: str
    confidence_score: float  # 0.0 to 1.0
    implementation_effort: str  # "low", "medium", "high"
    available_now: bool
    details: Dict[str, Any]
    alternatives: List[str]  # List of alternative integration IDs

@dataclass
class IntegrationRequest:
    """Request for new integration"""
    request_id: str
    user_id: UUID
    integration_name: str
    integration_url: Optional[str]
    category: IntegrationCategory
    description: str
    use_case: str
    priority: str  # "low", "medium", "high", "critical"
    business_impact: str
    expected_volume: int  # requests per month
    requested_at: datetime
    status: str  # "pending", "in_review", "approved", "rejected", "implemented"
    votes: int = 0
    comments: List[Dict[str, Any]] = None

class FallbackService:
    """Service for handling unsupported integrations"""
    
    def __init__(self):
        # Supported integrations with their capabilities
        self.supported_integrations = self._initialize_supported_integrations()
        
        # Third-party connector mappings
        self.third_party_connectors = self._initialize_third_party_connectors()
        
        # Integration requests storage (in production, would use database)
        self.integration_requests: Dict[str, IntegrationRequest] = {}
        
        # Common integration patterns for suggestions
        self.integration_patterns = self._initialize_integration_patterns()
        
        # Capability matching weights
        self.matching_weights = {
            'category': 0.3,
            'auth_method': 0.2,
            'data_format': 0.2,
            'endpoint_similarity': 0.3
        }
    
    def _initialize_supported_integrations(self) -> Dict[str, IntegrationCapability]:
        """Initialize supported integrations with their capabilities"""
        return {
            'gmail': IntegrationCapability(
                name="Gmail",
                description="Google Gmail API integration",
                category=IntegrationCategory.COMMUNICATION,
                required_auth=["oauth2"],
                endpoints=["/gmail/v1/users/me/messages", "/gmail/v1/users/me/messages/send"],
                data_formats=["json"]
            ),
            'whatsapp_business': IntegrationCapability(
                name="WhatsApp Business",
                description="WhatsApp Business API integration",
                category=IntegrationCategory.MESSAGING,
                required_auth=["api_key", "webhook_token"],
                endpoints=["/messages", "/media"],
                data_formats=["json"]
            ),
            'telegram': IntegrationCapability(
                name="Telegram Bot",
                description="Telegram Bot API integration",
                category=IntegrationCategory.MESSAGING,
                required_auth=["bot_token"],
                endpoints=["/sendMessage", "/sendPhoto", "/getUpdates"],
                data_formats=["json"]
            ),
            'supabase': IntegrationCapability(
                name="Supabase",
                description="Supabase database and auth integration",
                category=IntegrationCategory.DATABASE,
                required_auth=["api_key", "service_key"],
                endpoints=["/rest/v1/", "/auth/v1/"],
                data_formats=["json"]
            ),
            'http_generic': IntegrationCapability(
                name="Generic HTTP",
                description="Generic HTTP API integration",
                category=IntegrationCategory.OTHER,
                required_auth=["api_key", "bearer_token", "basic_auth"],
                endpoints=["/*"],
                data_formats=["json", "xml", "form_data", "text"]
            )
        }
    
    def _initialize_third_party_connectors(self) -> Dict[str, Dict[str, Any]]:
        """Initialize third-party connector mappings"""
        return {
            'zapier': {
                'name': 'Zapier',
                'description': 'Connect with 5000+ apps through Zapier',
                'webhook_url': 'https://hooks.zapier.com/hooks/catch/',
                'supported_apps': ['slack', 'trello', 'asana', 'notion', 'airtable', 'hubspot'],
                'pricing': 'free_tier_available',
                'setup_complexity': 'low'
            },
            'make': {
                'name': 'Make (formerly Integromat)',
                'description': 'Visual automation platform with 1000+ integrations',
                'webhook_url': 'https://hook.integromat.com/',
                'supported_apps': ['google_sheets', 'salesforce', 'shopify', 'mailchimp'],
                'pricing': 'free_tier_available',
                'setup_complexity': 'medium'
            },
            'n8n': {
                'name': 'n8n',
                'description': 'Open-source workflow automation',
                'webhook_url': 'configurable',
                'supported_apps': ['github', 'discord', 'stripe', 'typeform'],
                'pricing': 'open_source',
                'setup_complexity': 'high'
            },
            'pipedream': {
                'name': 'Pipedream',
                'description': 'Developer-first integration platform',
                'webhook_url': 'https://webhook.pipedream.com/',
                'supported_apps': ['twitter', 'linkedin', 'youtube', 'twilio'],
                'pricing': 'free_tier_available',
                'setup_complexity': 'medium'
            }
        }
    
    def _initialize_integration_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common integration patterns for matching"""
        return {
            'email_providers': {
                'keywords': ['email', 'mail', 'smtp', 'imap'],
                'category': IntegrationCategory.COMMUNICATION,
                'similar_to': ['gmail'],
                'common_endpoints': ['/send', '/inbox', '/messages']
            },
            'messaging_platforms': {
                'keywords': ['message', 'chat', 'sms', 'notification'],
                'category': IntegrationCategory.MESSAGING,
                'similar_to': ['whatsapp_business', 'telegram'],
                'common_endpoints': ['/send', '/webhook', '/messages']
            },
            'databases': {
                'keywords': ['database', 'db', 'sql', 'nosql', 'storage'],
                'category': IntegrationCategory.DATABASE,
                'similar_to': ['supabase'],
                'common_endpoints': ['/query', '/insert', '/update', '/delete']
            },
            'crm_systems': {
                'keywords': ['crm', 'customer', 'lead', 'contact', 'sales'],
                'category': IntegrationCategory.CRM,
                'similar_to': ['http_generic'],
                'common_endpoints': ['/contacts', '/leads', '/deals', '/accounts']
            },
            'social_media': {
                'keywords': ['social', 'post', 'share', 'follow', 'like'],
                'category': IntegrationCategory.SOCIAL_MEDIA,
                'similar_to': ['http_generic'],
                'common_endpoints': ['/posts', '/users', '/media', '/comments']
            }
        }
    
    async def handle_unsupported_integration(
        self,
        integration_name: str,
        user_id: UUID,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle request for unsupported integration"""
        logger.info(f"Handling unsupported integration request: {integration_name}")
        
        # Analyze the integration request
        analysis = await self._analyze_integration_request(integration_name, context)
        
        # Generate suggestions
        suggestions = await self._generate_suggestions(integration_name, analysis, context)
        
        # Record the request for analytics
        await self._record_integration_request(integration_name, user_id, analysis, context)
        
        return {
            'integration_name': integration_name,
            'supported': False,
            'analysis': analysis,
            'suggestions': [
                {
                    'suggestion_id': s.suggestion_id,
                    'type': s.suggestion_type.value,
                    'title': s.title,
                    'description': s.description,
                    'confidence_score': s.confidence_score,
                    'implementation_effort': s.implementation_effort,
                    'available_now': s.available_now,
                    'details': s.details,
                    'alternatives': s.alternatives
                } for s in suggestions
            ],
            'can_use_generic_http': analysis.get('has_api', False),
            'third_party_options': self._get_third_party_options(integration_name, analysis),
            'request_integration_url': f"/api/v1/integrations/request",
            'estimated_development_time': analysis.get('estimated_dev_time', 'unknown')
        }
    
    async def _analyze_integration_request(
        self,
        integration_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze integration request to understand requirements"""
        analysis = {
            'integration_name': integration_name,
            'detected_category': self._detect_category(integration_name),
            'has_api': self._likely_has_api(integration_name),
            'common_use_cases': self._get_common_use_cases(integration_name),
            'estimated_dev_time': self._estimate_development_time(integration_name),
            'complexity_score': self._calculate_complexity_score(integration_name),
            'market_demand': await self._get_market_demand(integration_name)
        }
        
        # Add context-specific analysis
        if context:
            analysis['user_context'] = context
            analysis['specific_use_case'] = context.get('use_case', 'general')
            analysis['required_features'] = context.get('required_features', [])
        
        return analysis
    
    def _detect_category(self, integration_name: str) -> IntegrationCategory:
        """Detect integration category based on name and patterns"""
        name_lower = integration_name.lower()
        
        for pattern_name, pattern_info in self.integration_patterns.items():
            for keyword in pattern_info['keywords']:
                if keyword in name_lower:
                    return pattern_info['category']
        
        # Check for specific service patterns
        if any(word in name_lower for word in ['slack', 'discord', 'teams', 'chat']):
            return IntegrationCategory.MESSAGING
        elif any(word in name_lower for word in ['salesforce', 'hubspot', 'pipedrive']):
            return IntegrationCategory.CRM
        elif any(word in name_lower for word in ['shopify', 'woocommerce', 'magento']):
            return IntegrationCategory.ECOMMERCE
        elif any(word in name_lower for word in ['stripe', 'paypal', 'payment']):
            return IntegrationCategory.PAYMENT
        elif any(word in name_lower for word in ['google', 'facebook', 'twitter', 'linkedin']):
            return IntegrationCategory.SOCIAL_MEDIA
        
        return IntegrationCategory.OTHER
    
    def _likely_has_api(self, integration_name: str) -> bool:
        """Determine if integration likely has an API"""
        name_lower = integration_name.lower()
        
        # Well-known services that definitely have APIs
        api_services = [
            'slack', 'discord', 'telegram', 'whatsapp', 'twitter', 'facebook',
            'google', 'microsoft', 'salesforce', 'hubspot', 'stripe', 'paypal',
            'shopify', 'woocommerce', 'github', 'gitlab', 'jira', 'trello',
            'notion', 'airtable', 'mailchimp', 'sendgrid', 'twilio'
        ]
        
        return any(service in name_lower for service in api_services)
    
    def _get_common_use_cases(self, integration_name: str) -> List[str]:
        """Get common use cases for the integration"""
        category = self._detect_category(integration_name)
        
        use_cases_by_category = {
            IntegrationCategory.COMMUNICATION: [
                "Send notifications", "Sync contacts", "Automate email responses"
            ],
            IntegrationCategory.MESSAGING: [
                "Send messages", "Receive webhooks", "Automate responses", "Broadcast updates"
            ],
            IntegrationCategory.DATABASE: [
                "Store data", "Query records", "Sync databases", "Backup data"
            ],
            IntegrationCategory.CRM: [
                "Sync contacts", "Update deals", "Track leads", "Generate reports"
            ],
            IntegrationCategory.ECOMMERCE: [
                "Sync orders", "Update inventory", "Process payments", "Send receipts"
            ],
            IntegrationCategory.SOCIAL_MEDIA: [
                "Post content", "Monitor mentions", "Analyze engagement", "Schedule posts"
            ]
        }
        
        return use_cases_by_category.get(category, ["Data synchronization", "Automation", "Notifications"])
    
    def _estimate_development_time(self, integration_name: str) -> str:
        """Estimate development time for the integration"""
        if self._likely_has_api(integration_name):
            complexity = self._calculate_complexity_score(integration_name)
            if complexity < 0.3:
                return "1-2 weeks"
            elif complexity < 0.6:
                return "2-4 weeks"
            else:
                return "4-8 weeks"
        else:
            return "8+ weeks (requires research)"
    
    def _calculate_complexity_score(self, integration_name: str) -> float:
        """Calculate complexity score (0.0 to 1.0)"""
        name_lower = integration_name.lower()
        
        # Simple services (low complexity)
        if any(service in name_lower for service in ['webhook', 'http', 'rest', 'api']):
            return 0.2
        
        # Well-documented services (medium complexity)
        if any(service in name_lower for service in ['slack', 'discord', 'telegram', 'stripe']):
            return 0.4
        
        # Enterprise services (high complexity)
        if any(service in name_lower for service in ['salesforce', 'sap', 'oracle', 'microsoft']):
            return 0.8
        
        # Unknown services (medium-high complexity)
        return 0.6
    
    async def _get_market_demand(self, integration_name: str) -> Dict[str, Any]:
        """Get market demand information for the integration"""
        # In production, this would query actual request data
        request_count = len([
            req for req in self.integration_requests.values()
            if integration_name.lower() in req.integration_name.lower()
        ])
        
        return {
            'request_count': request_count,
            'demand_level': 'high' if request_count > 10 else 'medium' if request_count > 3 else 'low',
            'last_requested': datetime.utcnow().isoformat() if request_count > 0 else None
        }
    
    async def _generate_suggestions(
        self,
        integration_name: str,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[IntegrationSuggestion]:
        """Generate suggestions for unsupported integration"""
        suggestions = []
        
        # 1. Direct alternatives (similar existing integrations)
        direct_alternatives = self._find_direct_alternatives(integration_name, analysis)
        for alt in direct_alternatives:
            suggestions.append(IntegrationSuggestion(
                suggestion_id=str(uuid4()),
                suggestion_type=SuggestionType.DIRECT_ALTERNATIVE,
                title=f"Use {alt['name']} instead",
                description=f"{alt['name']} provides similar functionality to {integration_name}",
                confidence_score=alt['similarity_score'],
                implementation_effort="low",
                available_now=True,
                details=alt,
                alternatives=[alt['integration_id']]
            ))
        
        # 2. Generic HTTP agent (if has API)
        if analysis.get('has_api', False):
            suggestions.append(IntegrationSuggestion(
                suggestion_id=str(uuid4()),
                suggestion_type=SuggestionType.GENERIC_HTTP,
                title="Use Generic HTTP Agent",
                description=f"Connect to {integration_name} using our generic HTTP agent with custom API calls",
                confidence_score=0.8,
                implementation_effort="medium",
                available_now=True,
                details={
                    'agent_id': 'sa-http-generic',
                    'setup_guide': f"/docs/integrations/http-generic",
                    'required_info': ['API endpoint', 'Authentication method', 'Request format']
                },
                alternatives=['http_generic']
            ))
        
        # 3. Third-party connectors
        third_party_options = self._get_third_party_options(integration_name, analysis)
        for connector in third_party_options:
            suggestions.append(IntegrationSuggestion(
                suggestion_id=str(uuid4()),
                suggestion_type=SuggestionType.THIRD_PARTY_CONNECTOR,
                title=f"Connect via {connector['name']}",
                description=f"Use {connector['name']} to connect with {integration_name}",
                confidence_score=0.7,
                implementation_effort=connector['setup_complexity'],
                available_now=True,
                details=connector,
                alternatives=[]
            ))
        
        # 4. Custom development suggestion
        suggestions.append(IntegrationSuggestion(
            suggestion_id=str(uuid4()),
            suggestion_type=SuggestionType.CUSTOM_DEVELOPMENT,
            title="Request Custom Integration",
            description=f"We can develop a native {integration_name} integration based on demand",
            confidence_score=0.9,
            implementation_effort="high",
            available_now=False,
            details={
                'estimated_time': analysis.get('estimated_dev_time', 'unknown'),
                'complexity_score': analysis.get('complexity_score', 0.5),
                'request_url': '/api/v1/integrations/request'
            },
            alternatives=[]
        ))
        
        # Sort by confidence score
        suggestions.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _find_direct_alternatives(
        self,
        integration_name: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find direct alternatives from supported integrations"""
        alternatives = []
        target_category = analysis.get('detected_category', IntegrationCategory.OTHER)
        
        for integration_id, capability in self.supported_integrations.items():
            if capability.category == target_category:
                similarity_score = self._calculate_similarity_score(
                    integration_name, capability, analysis
                )
                
                if similarity_score > 0.3:  # Minimum similarity threshold
                    alternatives.append({
                        'integration_id': integration_id,
                        'name': capability.name,
                        'description': capability.description,
                        'similarity_score': similarity_score,
                        'category': capability.category.value,
                        'auth_methods': capability.required_auth,
                        'data_formats': capability.data_formats
                    })
        
        return sorted(alternatives, key=lambda x: x['similarity_score'], reverse=True)
    
    def _calculate_similarity_score(
        self,
        integration_name: str,
        capability: IntegrationCapability,
        analysis: Dict[str, Any]
    ) -> float:
        """Calculate similarity score between requested and existing integration"""
        score = 0.0
        
        # Category match
        if capability.category == analysis.get('detected_category'):
            score += self.matching_weights['category']
        
        # Name similarity (simple keyword matching)
        name_words = set(integration_name.lower().split())
        capability_words = set(capability.name.lower().split())
        if name_words & capability_words:
            score += 0.2
        
        # Use case similarity
        common_use_cases = analysis.get('common_use_cases', [])
        capability_use_cases = self._get_common_use_cases(capability.name)
        if set(common_use_cases) & set(capability_use_cases):
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_third_party_options(
        self,
        integration_name: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get third-party connector options"""
        options = []
        
        for connector_id, connector_info in self.third_party_connectors.items():
            # Check if integration is in supported apps
            if any(app in integration_name.lower() for app in connector_info.get('supported_apps', [])):
                options.append({
                    'connector_id': connector_id,
                    'name': connector_info['name'],
                    'description': connector_info['description'],
                    'webhook_url': connector_info['webhook_url'],
                    'pricing': connector_info['pricing'],
                    'setup_complexity': connector_info['setup_complexity'],
                    'setup_guide': f"/docs/third-party/{connector_id}"
                })
        
        return options
    
    async def _record_integration_request(
        self,
        integration_name: str,
        user_id: UUID,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record integration request for analytics"""
        try:
            # Record in analytics
            await analytics_service.metrics_collector.increment_counter(
                'unsupported_integration_requests',
                tags={
                    'integration_name': integration_name,
                    'category': analysis.get('detected_category', {}).get('value', 'unknown'),
                    'has_api': str(analysis.get('has_api', False))
                }
            )
            
            # Record request details
            await analytics_service.metrics_collector.record_metric(
                'integration_request_complexity',
                analysis.get('complexity_score', 0.5),
                tags={'integration_name': integration_name}
            )
            
        except Exception as e:
            logger.error(f"Failed to record integration request: {e}")
    
    async def create_integration_request(
        self,
        user_id: UUID,
        integration_name: str,
        description: str,
        use_case: str,
        priority: str = "medium",
        integration_url: Optional[str] = None,
        business_impact: str = "",
        expected_volume: int = 100
    ) -> str:
        """Create a formal integration request"""
        request_id = str(uuid4())
        
        # Detect category
        category = self._detect_category(integration_name)
        
        request = IntegrationRequest(
            request_id=request_id,
            user_id=user_id,
            integration_name=integration_name,
            integration_url=integration_url,
            category=category,
            description=description,
            use_case=use_case,
            priority=priority,
            business_impact=business_impact,
            expected_volume=expected_volume,
            requested_at=datetime.utcnow(),
            status="pending",
            comments=[]
        )
        
        self.integration_requests[request_id] = request
        
        # Record in analytics
        await analytics_service.metrics_collector.increment_counter(
            'integration_requests_created',
            tags={
                'category': category.value,
                'priority': priority
            }
        )
        
        logger.info(f"Integration request created: {integration_name} by {user_id}")
        
        return request_id
    
    async def vote_for_integration_request(
        self,
        request_id: str,
        user_id: UUID
    ) -> bool:
        """Vote for an integration request"""
        request = self.integration_requests.get(request_id)
        if not request:
            return False
        
        request.votes += 1
        
        # Record vote in analytics
        await analytics_service.metrics_collector.increment_counter(
            'integration_request_votes',
            tags={'integration_name': request.integration_name}
        )
        
        return True
    
    async def get_integration_requests(
        self,
        status: Optional[str] = None,
        category: Optional[IntegrationCategory] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get integration requests with filtering"""
        requests = list(self.integration_requests.values())
        
        # Apply filters
        if status:
            requests = [r for r in requests if r.status == status]
        if category:
            requests = [r for r in requests if r.category == category]
        
        # Sort by votes and date
        requests.sort(key=lambda x: (x.votes, x.requested_at), reverse=True)
        
        # Apply pagination
        requests = requests[offset:offset + limit]
        
        return [
            {
                'request_id': r.request_id,
                'integration_name': r.integration_name,
                'integration_url': r.integration_url,
                'category': r.category.value,
                'description': r.description,
                'use_case': r.use_case,
                'priority': r.priority,
                'business_impact': r.business_impact,
                'expected_volume': r.expected_volume,
                'votes': r.votes,
                'status': r.status,
                'requested_at': r.requested_at.isoformat(),
                'comments_count': len(r.comments or [])
            } for r in requests
        ]
    
    async def get_integration_roadmap(self) -> Dict[str, Any]:
        """Get integration development roadmap"""
        requests = list(self.integration_requests.values())
        
        # Group by status
        by_status = {}
        for request in requests:
            if request.status not in by_status:
                by_status[request.status] = []
            by_status[request.status].append(request)
        
        # Get top requested integrations
        top_requests = sorted(requests, key=lambda x: x.votes, reverse=True)[:10]
        
        # Calculate development priorities
        priorities = self._calculate_development_priorities(requests)
        
        return {
            'total_requests': len(requests),
            'by_status': {
                status: len(reqs) for status, reqs in by_status.items()
            },
            'top_requested': [
                {
                    'integration_name': r.integration_name,
                    'votes': r.votes,
                    'category': r.category.value,
                    'priority': r.priority,
                    'status': r.status
                } for r in top_requests
            ],
            'development_priorities': priorities,
            'estimated_completion': self._estimate_roadmap_completion(requests)
        }
    
    def _calculate_development_priorities(
        self,
        requests: List[IntegrationRequest]
    ) -> List[Dict[str, Any]]:
        """Calculate development priorities based on votes, business impact, etc."""
        priorities = []
        
        for request in requests:
            if request.status in ['pending', 'in_review', 'approved']:
                priority_score = (
                    request.votes * 0.4 +
                    {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}.get(request.priority, 2) * 0.3 +
                    (request.expected_volume / 1000) * 0.3
                )
                
                priorities.append({
                    'request_id': request.request_id,
                    'integration_name': request.integration_name,
                    'priority_score': priority_score,
                    'votes': request.votes,
                    'business_priority': request.priority,
                    'category': request.category.value
                })
        
        return sorted(priorities, key=lambda x: x['priority_score'], reverse=True)[:20]
    
    def _estimate_roadmap_completion(
        self,
        requests: List[IntegrationRequest]
    ) -> Dict[str, Any]:
        """Estimate roadmap completion timeline"""
        approved_requests = [r for r in requests if r.status == 'approved']
        
        # Simple estimation based on complexity
        total_weeks = 0
        for request in approved_requests:
            complexity = self._calculate_complexity_score(request.integration_name)
            weeks = int(complexity * 8) + 2  # 2-8 weeks based on complexity
            total_weeks += weeks
        
        return {
            'approved_integrations': len(approved_requests),
            'estimated_total_weeks': total_weeks,
            'estimated_completion_date': (
                datetime.utcnow() + timedelta(weeks=total_weeks)
            ).isoformat() if total_weeks > 0 else None,
            'next_releases': [
                {
                    'quarter': f"Q{((datetime.utcnow().month - 1) // 3) + 1 + i} {datetime.utcnow().year}",
                    'integrations': min(3, len(approved_requests) - i * 3)
                } for i in range(4) if len(approved_requests) > i * 3
            ]
        }

# Global fallback service instance
fallback_service = FallbackService()