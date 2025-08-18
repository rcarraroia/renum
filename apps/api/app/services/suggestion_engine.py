"""
Suggestion Engine
Advanced suggestion engine based on capabilities and user context
"""
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import re
from dataclasses import dataclass
from collections import defaultdict
import difflib

from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class MatchingStrategy(Enum):
    """Strategies for matching integrations"""
    EXACT_MATCH = "exact_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CAPABILITY_BASED = "capability_based"
    USE_CASE_BASED = "use_case_based"
    HYBRID = "hybrid"

@dataclass
class CapabilityMatch:
    """Represents a capability match"""
    capability_name: str
    match_score: float
    match_type: str  # "exact", "similar", "related"
    explanation: str

@dataclass
class IntegrationMatch:
    """Represents an integration match"""
    integration_id: str
    integration_name: str
    match_score: float
    capability_matches: List[CapabilityMatch]
    pros: List[str]
    cons: List[str]
    setup_complexity: str
    estimated_setup_time: str
    cost_comparison: Dict[str, Any]

class SuggestionEngine:
    """Advanced suggestion engine for integration alternatives"""
    
    def __init__(self):
        # Capability taxonomy
        self.capability_taxonomy = self._build_capability_taxonomy()
        
        # Integration capability mappings
        self.integration_capabilities = self._build_integration_capabilities()
        
        # Semantic similarity mappings
        self.semantic_mappings = self._build_semantic_mappings()
        
        # Use case patterns
        self.use_case_patterns = self._build_use_case_patterns()
        
        # Matching weights for different strategies
        self.matching_weights = {
            'exact_capability': 1.0,
            'similar_capability': 0.8,
            'related_capability': 0.6,
            'semantic_similarity': 0.7,
            'use_case_match': 0.9,
            'category_match': 0.5
        }
    
    def _build_capability_taxonomy(self) -> Dict[str, Dict[str, Any]]:
        """Build hierarchical capability taxonomy"""
        return {
            'messaging': {
                'send_message': {
                    'aliases': ['send', 'post', 'publish', 'transmit'],
                    'related': ['broadcast', 'notify', 'alert'],
                    'parameters': ['recipient', 'content', 'format']
                },
                'receive_message': {
                    'aliases': ['receive', 'get', 'fetch', 'retrieve'],
                    'related': ['listen', 'monitor', 'watch'],
                    'parameters': ['source', 'filter', 'format']
                },
                'manage_contacts': {
                    'aliases': ['contacts', 'users', 'subscribers'],
                    'related': ['groups', 'lists', 'audiences'],
                    'parameters': ['contact_info', 'groups', 'metadata']
                }
            },
            'data_storage': {
                'create_record': {
                    'aliases': ['insert', 'add', 'create', 'store'],
                    'related': ['save', 'persist', 'write'],
                    'parameters': ['data', 'table', 'schema']
                },
                'read_record': {
                    'aliases': ['select', 'get', 'fetch', 'query'],
                    'related': ['search', 'find', 'retrieve'],
                    'parameters': ['filters', 'fields', 'limit']
                },
                'update_record': {
                    'aliases': ['update', 'modify', 'edit', 'change'],
                    'related': ['patch', 'merge', 'upsert'],
                    'parameters': ['id', 'data', 'conditions']
                },
                'delete_record': {
                    'aliases': ['delete', 'remove', 'destroy'],
                    'related': ['purge', 'clear', 'drop'],
                    'parameters': ['id', 'conditions', 'cascade']
                }
            },
            'authentication': {
                'oauth2': {
                    'aliases': ['oauth', 'oauth2.0', 'social_login'],
                    'related': ['sso', 'openid', 'saml'],
                    'parameters': ['client_id', 'client_secret', 'scopes']
                },
                'api_key': {
                    'aliases': ['token', 'key', 'secret'],
                    'related': ['bearer_token', 'access_token'],
                    'parameters': ['key', 'header', 'query_param']
                },
                'basic_auth': {
                    'aliases': ['username_password', 'credentials'],
                    'related': ['digest_auth', 'ntlm'],
                    'parameters': ['username', 'password', 'realm']
                }
            },
            'file_operations': {
                'upload_file': {
                    'aliases': ['upload', 'send_file', 'attach'],
                    'related': ['store_file', 'save_file'],
                    'parameters': ['file', 'destination', 'metadata']
                },
                'download_file': {
                    'aliases': ['download', 'get_file', 'fetch_file'],
                    'related': ['retrieve_file', 'load_file'],
                    'parameters': ['file_id', 'path', 'format']
                }
            },
            'notifications': {
                'send_notification': {
                    'aliases': ['notify', 'alert', 'inform'],
                    'related': ['broadcast', 'announce', 'push'],
                    'parameters': ['recipient', 'message', 'channel']
                },
                'subscribe': {
                    'aliases': ['listen', 'watch', 'monitor'],
                    'related': ['follow', 'track', 'observe'],
                    'parameters': ['event', 'callback', 'filters']
                }
            }
        }
    
    def _build_integration_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Build detailed capability mappings for each integration"""
        return {
            'gmail': {
                'primary_capabilities': [
                    'send_message', 'receive_message', 'manage_contacts',
                    'search_messages', 'manage_labels', 'upload_file'
                ],
                'authentication': ['oauth2'],
                'data_formats': ['json', 'mime'],
                'rate_limits': {'requests_per_minute': 250},
                'strengths': [
                    'Reliable email delivery',
                    'Rich search capabilities',
                    'Excellent documentation',
                    'High deliverability rates'
                ],
                'limitations': [
                    'OAuth setup complexity',
                    'Rate limiting',
                    'Google account required'
                ],
                'use_cases': [
                    'Email automation',
                    'Newsletter sending',
                    'Transactional emails',
                    'Email monitoring'
                ]
            },
            'whatsapp_business': {
                'primary_capabilities': [
                    'send_message', 'receive_message', 'send_notification',
                    'upload_file', 'manage_contacts', 'send_template'
                ],
                'authentication': ['api_key', 'webhook_token'],
                'data_formats': ['json'],
                'rate_limits': {'messages_per_second': 20},
                'strengths': [
                    'High engagement rates',
                    'Rich media support',
                    'Global reach',
                    'Business verification'
                ],
                'limitations': [
                    'Template approval required',
                    'Business account needed',
                    'Strict policies',
                    'Cost per message'
                ],
                'use_cases': [
                    'Customer support',
                    'Order notifications',
                    'Marketing campaigns',
                    'Two-way communication'
                ]
            },
            'telegram': {
                'primary_capabilities': [
                    'send_message', 'receive_message', 'send_notification',
                    'upload_file', 'manage_groups', 'inline_keyboards'
                ],
                'authentication': ['bot_token'],
                'data_formats': ['json'],
                'rate_limits': {'messages_per_second': 30},
                'strengths': [
                    'Easy bot setup',
                    'Rich bot features',
                    'No message costs',
                    'Excellent API'
                ],
                'limitations': [
                    'Limited business features',
                    'Smaller user base',
                    'Bot limitations'
                ],
                'use_cases': [
                    'Bot automation',
                    'Group management',
                    'Notifications',
                    'Customer service'
                ]
            },
            'supabase': {
                'primary_capabilities': [
                    'create_record', 'read_record', 'update_record', 'delete_record',
                    'real_time_sync', 'authentication', 'file_storage'
                ],
                'authentication': ['api_key', 'service_key', 'oauth2'],
                'data_formats': ['json', 'postgresql'],
                'rate_limits': {'requests_per_minute': 1000},
                'strengths': [
                    'Real-time capabilities',
                    'Built-in authentication',
                    'PostgreSQL compatibility',
                    'Easy scaling'
                ],
                'limitations': [
                    'Vendor lock-in',
                    'Learning curve',
                    'Pricing at scale'
                ],
                'use_cases': [
                    'Web applications',
                    'Real-time apps',
                    'User management',
                    'Data storage'
                ]
            },
            'http_generic': {
                'primary_capabilities': [
                    'http_request', 'custom_headers', 'multiple_auth',
                    'data_transformation', 'error_handling'
                ],
                'authentication': ['api_key', 'oauth2', 'basic_auth', 'bearer_token'],
                'data_formats': ['json', 'xml', 'form_data', 'text', 'binary'],
                'rate_limits': {'configurable': True},
                'strengths': [
                    'Maximum flexibility',
                    'Any REST API',
                    'Custom authentication',
                    'Data transformation'
                ],
                'limitations': [
                    'Requires API knowledge',
                    'Manual configuration',
                    'No built-in features'
                ],
                'use_cases': [
                    'Custom API integration',
                    'Legacy system connection',
                    'Prototype development',
                    'Unsupported services'
                ]
            }
        }
    
    def _build_semantic_mappings(self) -> Dict[str, List[str]]:
        """Build semantic similarity mappings"""
        return {
            'email': ['mail', 'message', 'communication', 'notification', 'letter'],
            'message': ['text', 'communication', 'chat', 'notification', 'alert'],
            'database': ['storage', 'data', 'records', 'table', 'repository'],
            'api': ['service', 'endpoint', 'interface', 'integration', 'connection'],
            'authentication': ['auth', 'login', 'security', 'credentials', 'access'],
            'file': ['document', 'attachment', 'media', 'upload', 'download'],
            'notification': ['alert', 'message', 'push', 'inform', 'notify'],
            'webhook': ['callback', 'event', 'trigger', 'listener', 'hook']
        }
    
    def _build_use_case_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build use case patterns for matching"""
        return {
            'customer_communication': {
                'keywords': ['customer', 'support', 'service', 'communication', 'chat'],
                'required_capabilities': ['send_message', 'receive_message'],
                'preferred_integrations': ['whatsapp_business', 'telegram', 'gmail'],
                'considerations': ['response_time', 'scalability', 'cost']
            },
            'data_synchronization': {
                'keywords': ['sync', 'data', 'database', 'records', 'backup'],
                'required_capabilities': ['create_record', 'read_record', 'update_record'],
                'preferred_integrations': ['supabase', 'http_generic'],
                'considerations': ['data_consistency', 'performance', 'reliability']
            },
            'automation_workflows': {
                'keywords': ['automation', 'workflow', 'trigger', 'process', 'pipeline'],
                'required_capabilities': ['send_notification', 'data_transformation'],
                'preferred_integrations': ['http_generic', 'webhook'],
                'considerations': ['flexibility', 'reliability', 'monitoring']
            },
            'marketing_campaigns': {
                'keywords': ['marketing', 'campaign', 'broadcast', 'newsletter', 'promotion'],
                'required_capabilities': ['send_message', 'manage_contacts', 'send_template'],
                'preferred_integrations': ['gmail', 'whatsapp_business'],
                'considerations': ['deliverability', 'compliance', 'analytics']
            }
        }
    
    async def suggest_alternatives(
        self,
        target_integration: str,
        required_capabilities: List[str],
        use_case: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
        strategy: MatchingStrategy = MatchingStrategy.HYBRID
    ) -> List[IntegrationMatch]:
        """Generate alternative integration suggestions"""
        logger.info(f"Generating suggestions for {target_integration} with strategy {strategy.value}")
        
        # Analyze target integration requirements
        target_analysis = await self._analyze_target_requirements(
            target_integration, required_capabilities, use_case, user_context
        )
        
        # Find matches using specified strategy
        matches = await self._find_matches(target_analysis, strategy)
        
        # Rank and filter matches
        ranked_matches = await self._rank_matches(matches, target_analysis)
        
        # Add detailed comparison information
        detailed_matches = await self._add_match_details(ranked_matches, target_analysis)
        
        return detailed_matches[:5]  # Return top 5 matches
    
    async def _analyze_target_requirements(
        self,
        target_integration: str,
        required_capabilities: List[str],
        use_case: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze target integration requirements"""
        analysis = {
            'target_integration': target_integration,
            'required_capabilities': required_capabilities,
            'use_case': use_case,
            'user_context': user_context or {},
            'inferred_capabilities': [],
            'priority_capabilities': [],
            'nice_to_have_capabilities': []
        }
        
        # Infer additional capabilities from integration name
        inferred_caps = self._infer_capabilities_from_name(target_integration)
        analysis['inferred_capabilities'] = inferred_caps
        
        # Analyze use case to determine priority capabilities
        if use_case:
            use_case_analysis = self._analyze_use_case(use_case)
            analysis['priority_capabilities'] = use_case_analysis.get('required_capabilities', [])
            analysis['nice_to_have_capabilities'] = use_case_analysis.get('optional_capabilities', [])
        
        # Combine all capabilities
        all_capabilities = set(required_capabilities + inferred_caps + analysis['priority_capabilities'])
        analysis['all_capabilities'] = list(all_capabilities)
        
        return analysis
    
    def _infer_capabilities_from_name(self, integration_name: str) -> List[str]:
        """Infer capabilities from integration name"""
        name_lower = integration_name.lower()
        inferred = []
        
        # Check semantic mappings
        for concept, related_terms in self.semantic_mappings.items():
            if any(term in name_lower for term in [concept] + related_terms):
                # Map concept to capabilities
                if concept == 'email':
                    inferred.extend(['send_message', 'receive_message', 'manage_contacts'])
                elif concept == 'message':
                    inferred.extend(['send_message', 'receive_message'])
                elif concept == 'database':
                    inferred.extend(['create_record', 'read_record', 'update_record', 'delete_record'])
                elif concept == 'file':
                    inferred.extend(['upload_file', 'download_file'])
                elif concept == 'notification':
                    inferred.extend(['send_notification'])
        
        # Check for specific service patterns
        service_patterns = {
            'slack': ['send_message', 'receive_message', 'manage_contacts', 'upload_file'],
            'discord': ['send_message', 'receive_message', 'manage_groups'],
            'salesforce': ['create_record', 'read_record', 'update_record', 'manage_contacts'],
            'stripe': ['create_record', 'read_record', 'webhook_handling'],
            'shopify': ['create_record', 'read_record', 'update_record', 'webhook_handling']
        }
        
        for service, capabilities in service_patterns.items():
            if service in name_lower:
                inferred.extend(capabilities)
        
        return list(set(inferred))
    
    def _analyze_use_case(self, use_case: str) -> Dict[str, Any]:
        """Analyze use case to determine capability requirements"""
        use_case_lower = use_case.lower()
        
        for pattern_name, pattern_info in self.use_case_patterns.items():
            if any(keyword in use_case_lower for keyword in pattern_info['keywords']):
                return {
                    'pattern': pattern_name,
                    'required_capabilities': pattern_info['required_capabilities'],
                    'optional_capabilities': [],
                    'preferred_integrations': pattern_info['preferred_integrations'],
                    'considerations': pattern_info['considerations']
                }
        
        # Default analysis
        return {
            'pattern': 'general',
            'required_capabilities': [],
            'optional_capabilities': [],
            'preferred_integrations': [],
            'considerations': ['functionality', 'ease_of_use', 'cost']
        }
    
    async def _find_matches(
        self,
        target_analysis: Dict[str, Any],
        strategy: MatchingStrategy
    ) -> List[Dict[str, Any]]:
        """Find integration matches using specified strategy"""
        matches = []
        
        for integration_id, integration_info in self.integration_capabilities.items():
            match_score = 0.0
            capability_matches = []
            
            if strategy in [MatchingStrategy.CAPABILITY_BASED, MatchingStrategy.HYBRID]:
                # Capability-based matching
                cap_score, cap_matches = self._calculate_capability_match(
                    target_analysis['all_capabilities'],
                    integration_info['primary_capabilities']
                )
                match_score += cap_score * 0.6
                capability_matches.extend(cap_matches)
            
            if strategy in [MatchingStrategy.SEMANTIC_SIMILARITY, MatchingStrategy.HYBRID]:
                # Semantic similarity matching
                sem_score = self._calculate_semantic_similarity(
                    target_analysis['target_integration'],
                    integration_id
                )
                match_score += sem_score * 0.3
            
            if strategy in [MatchingStrategy.USE_CASE_BASED, MatchingStrategy.HYBRID]:
                # Use case matching
                use_case_score = self._calculate_use_case_match(
                    target_analysis.get('use_case', ''),
                    integration_info.get('use_cases', [])
                )
                match_score += use_case_score * 0.1
            
            if match_score > 0.1:  # Minimum threshold
                matches.append({
                    'integration_id': integration_id,
                    'integration_info': integration_info,
                    'match_score': match_score,
                    'capability_matches': capability_matches
                })
        
        return matches
    
    def _calculate_capability_match(
        self,
        required_capabilities: List[str],
        available_capabilities: List[str]
    ) -> Tuple[float, List[CapabilityMatch]]:
        """Calculate capability match score"""
        if not required_capabilities:
            return 0.0, []
        
        matches = []
        total_score = 0.0
        
        for req_cap in required_capabilities:
            best_match = None
            best_score = 0.0
            
            for avail_cap in available_capabilities:
                # Exact match
                if req_cap == avail_cap:
                    match = CapabilityMatch(
                        capability_name=avail_cap,
                        match_score=1.0,
                        match_type="exact",
                        explanation=f"Exact match for {req_cap}"
                    )
                    best_match = match
                    best_score = 1.0
                    break
                
                # Semantic similarity
                similarity = self._calculate_capability_similarity(req_cap, avail_cap)
                if similarity > best_score:
                    match_type = "similar" if similarity > 0.7 else "related"
                    match = CapabilityMatch(
                        capability_name=avail_cap,
                        match_score=similarity,
                        match_type=match_type,
                        explanation=f"{avail_cap} is {match_type} to {req_cap}"
                    )
                    best_match = match
                    best_score = similarity
            
            if best_match and best_score > 0.3:  # Minimum similarity threshold
                matches.append(best_match)
                total_score += best_score
        
        # Calculate overall score
        overall_score = total_score / len(required_capabilities) if required_capabilities else 0.0
        
        return overall_score, matches
    
    def _calculate_capability_similarity(self, cap1: str, cap2: str) -> float:
        """Calculate similarity between two capabilities"""
        # Direct string similarity
        string_similarity = difflib.SequenceMatcher(None, cap1, cap2).ratio()
        
        # Check capability taxonomy for relationships
        taxonomy_similarity = 0.0
        for category, capabilities in self.capability_taxonomy.items():
            if cap1 in capabilities and cap2 in capabilities:
                cap1_info = capabilities[cap1]
                cap2_info = capabilities[cap2]
                
                # Check aliases
                if cap2 in cap1_info.get('aliases', []) or cap1 in cap2_info.get('aliases', []):
                    taxonomy_similarity = 0.9
                # Check related capabilities
                elif cap2 in cap1_info.get('related', []) or cap1 in cap2_info.get('related', []):
                    taxonomy_similarity = 0.7
        
        return max(string_similarity, taxonomy_similarity)
    
    def _calculate_semantic_similarity(self, target_name: str, integration_name: str) -> float:
        """Calculate semantic similarity between integration names"""
        target_lower = target_name.lower()
        integration_lower = integration_name.lower()
        
        # Direct string similarity
        string_sim = difflib.SequenceMatcher(None, target_lower, integration_lower).ratio()
        
        # Semantic mapping similarity
        semantic_sim = 0.0
        for concept, related_terms in self.semantic_mappings.items():
            target_has_concept = any(term in target_lower for term in [concept] + related_terms)
            integration_has_concept = any(term in integration_lower for term in [concept] + related_terms)
            
            if target_has_concept and integration_has_concept:
                semantic_sim = max(semantic_sim, 0.6)
        
        return max(string_sim, semantic_sim)
    
    def _calculate_use_case_match(self, target_use_case: str, integration_use_cases: List[str]) -> float:
        """Calculate use case match score"""
        if not target_use_case or not integration_use_cases:
            return 0.0
        
        target_lower = target_use_case.lower()
        max_similarity = 0.0
        
        for use_case in integration_use_cases:
            similarity = difflib.SequenceMatcher(None, target_lower, use_case.lower()).ratio()
            max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    async def _rank_matches(
        self,
        matches: List[Dict[str, Any]],
        target_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rank matches based on various factors"""
        for match in matches:
            # Apply user context adjustments
            user_context = target_analysis.get('user_context', {})
            
            # Adjust for user preferences
            if 'preferred_auth' in user_context:
                preferred_auth = user_context['preferred_auth']
                if preferred_auth in match['integration_info'].get('authentication', []):
                    match['match_score'] *= 1.1
            
            # Adjust for complexity preference
            if 'complexity_preference' in user_context:
                complexity_pref = user_context['complexity_preference']
                integration_complexity = self._estimate_integration_complexity(match['integration_id'])
                
                if complexity_pref == 'simple' and integration_complexity < 0.5:
                    match['match_score'] *= 1.2
                elif complexity_pref == 'advanced' and integration_complexity > 0.7:
                    match['match_score'] *= 1.1
            
            # Adjust for cost sensitivity
            if 'cost_sensitive' in user_context and user_context['cost_sensitive']:
                if self._is_free_integration(match['integration_id']):
                    match['match_score'] *= 1.15
        
        # Sort by match score
        return sorted(matches, key=lambda x: x['match_score'], reverse=True)
    
    def _estimate_integration_complexity(self, integration_id: str) -> float:
        """Estimate integration complexity (0.0 to 1.0)"""
        complexity_scores = {
            'http_generic': 0.8,  # High complexity, requires API knowledge
            'gmail': 0.6,         # Medium complexity, OAuth setup
            'whatsapp_business': 0.7,  # Medium-high complexity, business verification
            'telegram': 0.3,      # Low complexity, simple bot setup
            'supabase': 0.5       # Medium complexity, database concepts
        }
        return complexity_scores.get(integration_id, 0.5)
    
    def _is_free_integration(self, integration_id: str) -> bool:
        """Check if integration is free to use"""
        free_integrations = ['telegram', 'http_generic']
        return integration_id in free_integrations
    
    async def _add_match_details(
        self,
        matches: List[Dict[str, Any]],
        target_analysis: Dict[str, Any]
    ) -> List[IntegrationMatch]:
        """Add detailed information to matches"""
        detailed_matches = []
        
        for match in matches:
            integration_id = match['integration_id']
            integration_info = match['integration_info']
            
            # Generate pros and cons
            pros, cons = self._generate_pros_cons(integration_info, target_analysis)
            
            # Estimate setup complexity and time
            setup_complexity, setup_time = self._estimate_setup_requirements(integration_id)
            
            # Generate cost comparison
            cost_comparison = self._generate_cost_comparison(integration_id, target_analysis)
            
            detailed_match = IntegrationMatch(
                integration_id=integration_id,
                integration_name=integration_info.get('name', integration_id),
                match_score=match['match_score'],
                capability_matches=match['capability_matches'],
                pros=pros,
                cons=cons,
                setup_complexity=setup_complexity,
                estimated_setup_time=setup_time,
                cost_comparison=cost_comparison
            )
            
            detailed_matches.append(detailed_match)
        
        return detailed_matches
    
    def _generate_pros_cons(
        self,
        integration_info: Dict[str, Any],
        target_analysis: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Generate pros and cons for the integration"""
        pros = integration_info.get('strengths', []).copy()
        cons = integration_info.get('limitations', []).copy()
        
        # Add context-specific pros/cons
        user_context = target_analysis.get('user_context', {})
        
        if user_context.get('cost_sensitive'):
            if 'No message costs' in pros or 'free' in str(integration_info).lower():
                pros.append('Cost-effective solution')
            else:
                cons.append('May have usage costs')
        
        if user_context.get('complexity_preference') == 'simple':
            if 'Easy' in str(pros) or 'Simple' in str(pros):
                pros.append('Simple to set up and use')
            else:
                cons.append('May require technical expertise')
        
        return pros[:5], cons[:5]  # Limit to 5 items each
    
    def _estimate_setup_requirements(self, integration_id: str) -> Tuple[str, str]:
        """Estimate setup complexity and time"""
        setup_info = {
            'telegram': ('Low', '15-30 minutes'),
            'http_generic': ('Medium', '1-2 hours'),
            'gmail': ('Medium-High', '2-4 hours'),
            'whatsapp_business': ('High', '1-2 days'),
            'supabase': ('Medium', '1-2 hours')
        }
        
        return setup_info.get(integration_id, ('Medium', '1-2 hours'))
    
    def _generate_cost_comparison(
        self,
        integration_id: str,
        target_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate cost comparison information"""
        cost_info = {
            'telegram': {
                'setup_cost': 0,
                'monthly_cost': 0,
                'per_message_cost': 0,
                'free_tier': 'Unlimited'
            },
            'gmail': {
                'setup_cost': 0,
                'monthly_cost': 0,
                'per_message_cost': 0,
                'free_tier': '100 requests/user/100 seconds'
            },
            'whatsapp_business': {
                'setup_cost': 0,
                'monthly_cost': 0,
                'per_message_cost': 0.005,  # $0.005 per message
                'free_tier': '1000 conversations/month'
            },
            'supabase': {
                'setup_cost': 0,
                'monthly_cost': 0,
                'per_request_cost': 0,
                'free_tier': '50,000 monthly active users'
            },
            'http_generic': {
                'setup_cost': 0,
                'monthly_cost': 0,
                'per_request_cost': 0,
                'free_tier': 'Depends on target API'
            }
        }
        
        return cost_info.get(integration_id, {
            'setup_cost': 'Unknown',
            'monthly_cost': 'Varies',
            'per_request_cost': 'Varies',
            'free_tier': 'Check with provider'
        })

# Global suggestion engine instance
suggestion_engine = SuggestionEngine()