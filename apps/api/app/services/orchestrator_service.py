"""
Orchestrator Service for multi-agent system
Handles conversational interface, plan generation, and workflow execution
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from app.domain.orchestrator import (
    Workflow, WorkflowExecution, ConversationSession,
    WorkflowStep, WorkflowConfig, ExecutionStrategy
)
from app.schemas.orchestrator import (
    ChatMessageSchema,
    OrchestratorResponseSchema,
    CreateWorkflowSchema,
    ExecuteWorkflowSchema,
    ExecutionPlanSchema
)
from app.services.agent_registry_service import AgentRegistryService
from app.services.integration_service import IntegrationService
from app.repositories.orchestrator_repository import OrchestratorRepository
from app.services.manifest_cache_service import manifest_cache_service


class OrchestratorService:
    """Service for orchestrating multi-agent workflows with conversational interface"""
    
    def __init__(
        self,
        orchestrator_repository: Optional[OrchestratorRepository] = None,
        agent_registry_service: Optional[AgentRegistryService] = None,
        integration_service: Optional[IntegrationService] = None
    ):
        self.orchestrator_repo = orchestrator_repository or OrchestratorRepository()
        self.agent_registry = agent_registry_service or AgentRegistryService()
        self.integration_service = integration_service or IntegrationService()
    
    async def process_user_message(
        self, 
        user_id: UUID, 
        message: ChatMessageSchema
    ) -> OrchestratorResponseSchema:
        """Process user message and generate response"""
        
        # Get or create conversation session
        session = await self._get_or_create_session(user_id, message.session_id)
        
        # Add user message to conversation
        session.add_message('user', message.message, message.context)
        
        # Analyze user intent and requirements
        intent_analysis = await self._analyze_user_intent(message.message, session.context)
        
        # Update session context
        session.update_context('last_intent', intent_analysis)
        
        # Generate response based on conversation state
        if session.current_workflow is None:
            # Starting new workflow conversation
            response = await self._handle_initial_conversation(session, intent_analysis)
        else:
            # Continuing existing workflow conversation
            response = await self._handle_workflow_conversation(session, intent_analysis)
        
        # Add assistant response to conversation
        session.add_message('assistant', response.message)
        
        # Save session
        await self.orchestrator_repo.save_conversation_session(session)
        
        return response
    
    async def generate_execution_plan(
        self, 
        requirements: Dict[str, Any], 
        user_id: UUID
    ) -> ExecutionPlanSchema:
        """Generate multi-agent execution plan"""
        
        # Analyze requirements and select appropriate agents
        selected_agents = await self._select_agents_for_requirements(requirements)
        
        # Generate workflow steps
        steps = await self._generate_workflow_steps(requirements, selected_agents)
        
        # Create workflow
        workflow = await self._create_workflow_from_steps(user_id, requirements, steps)
        
        # Estimate cost and duration
        estimated_cost = await self._estimate_workflow_cost(workflow)
        estimated_duration = await self._estimate_workflow_duration(workflow)
        
        # Check required connections
        required_connections = await self._get_required_connections(workflow)
        
        # Identify risks
        risks = await self._identify_workflow_risks(workflow, requirements)
        
        return ExecutionPlanSchema(
            plan_id=f"plan_{uuid4().hex[:12]}",
            description=await self._generate_plan_description(requirements, workflow),
            workflow=await self._workflow_to_create_schema(workflow),
            estimated_cost=estimated_cost,
            estimated_duration_minutes=estimated_duration,
            required_connections=required_connections,
            risks=risks
        )
    
    async def execute_workflow(
        self, 
        execute_data: ExecuteWorkflowSchema,
        user_id: UUID
    ) -> WorkflowExecution:
        """Execute approved workflow"""
        
        # Get workflow
        workflow = await self.orchestrator_repo.find_workflow_by_id(execute_data.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {execute_data.workflow_id} not found")
        
        # Validate user ownership
        if workflow.user_id != user_id:
            raise ValueError("Workflow not owned by user")
        
        # Create execution
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            user_id=user_id,
            input_data=execute_data.input_data
        )
        
        # Start execution
        execution.start_execution()
        execution.add_log('info', f'Starting workflow execution: {workflow.name}')
        
        # Save initial execution state
        await self.orchestrator_repo.save_workflow_execution(execution)
        
        # Execute workflow steps based on strategy
        if execute_data.dry_run:
            execution = await self._dry_run_workflow(workflow, execution)
        else:
            execution = await self._execute_workflow_steps(workflow, execution)
        
        # Save final execution state
        return await self.orchestrator_repo.save_workflow_execution(execution)
    
    async def get_user_workflows(
        self, 
        user_id: UUID,
        status: Optional[str] = None
    ) -> List[Workflow]:
        """Get user's workflows"""
        
        return await self.orchestrator_repo.find_workflows_by_user(user_id, status)
    
    async def get_user_executions(
        self, 
        user_id: UUID,
        status: Optional[str] = None
    ) -> List[WorkflowExecution]:
        """Get user's workflow executions"""
        
        return await self.orchestrator_repo.find_executions_by_user(user_id, status)
    
    async def cancel_execution(self, execution_id: UUID, user_id: UUID) -> WorkflowExecution:
        """Cancel running execution"""
        
        execution = await self.orchestrator_repo.find_execution_by_id(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        # Validate user ownership
        if execution.user_id != user_id:
            raise ValueError("Execution not owned by user")
        
        # Can only cancel running executions
        if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            raise ValueError(f"Cannot cancel execution with status: {execution.status.value}")
        
        # Cancel execution
        execution.cancel_execution()
        execution.add_log('warning', 'Execution cancelled by user')
        
        return await self.orchestrator_repo.save_workflow_execution(execution)
    
    # Private helper methods
    
    async def _get_or_create_session(
        self, 
        user_id: UUID, 
        session_id: Optional[str]
    ) -> ConversationSession:
        """Get existing session or create new one"""
        
        if session_id:
            session = await self.orchestrator_repo.find_conversation_session(session_id)
            if session and not session.is_expired():
                return session
        
        # Create new session
        session = ConversationSession(user_id=user_id)
        return await self.orchestrator_repo.save_conversation_session(session)
    
    async def _analyze_user_intent(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze user intent from message"""
        
        message_lower = message.lower()
        
        # Intent categories
        intents = {
            'create_workflow': ['criar', 'novo', 'workflow', 'automatizar', 'processo'],
            'send_email': ['email', 'enviar', 'mandar', 'notificar', 'avisar'],
            'send_message': ['mensagem', 'whatsapp', 'telegram', 'sms'],
            'process_data': ['processar', 'dados', 'planilha', 'csv', 'excel'],
            'integrate_system': ['integrar', 'conectar', 'sincronizar', 'api'],
            'schedule_task': ['agendar', 'programar', 'cronograma', 'horário'],
            'generate_report': ['relatório', 'report', 'análise', 'dashboard']
        }
        
        # Find matching intents
        detected_intents = []
        for intent, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_intents.append(intent)
        
        # Extract entities
        entities = {
            'emails': self._extract_emails(message),
            'phone_numbers': self._extract_phone_numbers(message),
            'urls': self._extract_urls(message),
            'dates': self._extract_dates(message),
            'numbers': self._extract_numbers(message)
        }
        
        return {
            'intents': detected_intents,
            'primary_intent': detected_intents[0] if detected_intents else 'general',
            'entities': entities,
            'confidence': len(detected_intents) * 0.3,  # Simple confidence scoring
            'requires_clarification': len(detected_intents) == 0 or len(detected_intents) > 2
        }
    
    async def _handle_initial_conversation(
        self, 
        session: ConversationSession, 
        intent_analysis: Dict[str, Any]
    ) -> OrchestratorResponseSchema:
        """Handle initial conversation to understand requirements"""
        
        primary_intent = intent_analysis['primary_intent']
        
        if intent_analysis['requires_clarification']:
            # Ask clarifying questions
            questions = await self._generate_clarifying_questions(intent_analysis)
            
            return OrchestratorResponseSchema(
                message=f"Entendi que você quer automatizar algo. {questions[0]}",
                session_id=session.session_id,
                requires_input=True,
                confidence_score=intent_analysis['confidence'],
                next_questions=questions[1:3] if len(questions) > 1 else []
            )
        
        # Generate initial workflow suggestion
        suggested_workflow = await self._generate_initial_workflow(session.user_id, intent_analysis)
        
        return OrchestratorResponseSchema(
            message=f"Baseado no que você disse, posso criar um workflow para {primary_intent}. Aqui está minha sugestão:",
            session_id=session.session_id,
            requires_input=True,
            suggested_workflow=suggested_workflow,
            confidence_score=intent_analysis['confidence']
        )
    
    async def _handle_workflow_conversation(
        self, 
        session: ConversationSession, 
        intent_analysis: Dict[str, Any]
    ) -> OrchestratorResponseSchema:
        """Handle conversation about existing workflow"""
        
        # This would handle refinement of existing workflow
        return OrchestratorResponseSchema(
            message="Vou refinar o workflow baseado no seu feedback.",
            session_id=session.session_id,
            requires_input=False,
            confidence_score=0.8
        )
    
    async def _select_agents_for_requirements(self, requirements: Dict[str, Any]) -> List[str]:
        """Select appropriate agents based on requirements"""
        
        # This would use the agent registry to find suitable agents
        # For now, return mock agents based on requirements
        
        required_capabilities = requirements.get('capabilities', [])
        selected_agents = []
        
        # Get available agents
        available_agents = await self.agent_registry.get_available_agents()
        
        for agent in available_agents:
            agent_capabilities = [cap.name for cap in agent.capabilities]
            
            # Check if agent has required capabilities
            if any(cap in agent_capabilities for cap in required_capabilities):
                selected_agents.append(agent.agent_id)
        
        return selected_agents
    
    async def _generate_workflow_steps(
        self, 
        requirements: Dict[str, Any], 
        selected_agents: List[str]
    ) -> List[WorkflowStep]:
        """Generate workflow steps based on requirements and selected agents"""
        
        steps = []
        
        # Simple step generation based on primary intent
        primary_intent = requirements.get('primary_intent', 'general')
        
        if primary_intent == 'send_email':
            steps.append(WorkflowStep(
                step_id='send_email_1',
                agent_id='sa-email-basic',
                action='send_email',
                input_data=requirements.get('email_data', {})
            ))
        
        elif primary_intent == 'send_message':
            if 'whatsapp' in requirements.get('platforms', []):
                steps.append(WorkflowStep(
                    step_id='send_whatsapp_1',
                    agent_id='sa-whatsapp',
                    action='send_message',
                    input_data=requirements.get('message_data', {})
                ))
        
        elif primary_intent == 'process_data':
            steps.append(WorkflowStep(
                step_id='process_data_1',
                agent_id='sa-supabase',
                action='query_database',
                input_data=requirements.get('data_query', {})
            ))
        
        return steps
    
    async def _create_workflow_from_steps(
        self, 
        user_id: UUID, 
        requirements: Dict[str, Any], 
        steps: List[WorkflowStep]
    ) -> Workflow:
        """Create workflow from generated steps"""
        
        config = WorkflowConfig(
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            timeout_minutes=requirements.get('timeout_minutes', 30)
        )
        
        workflow = Workflow(
            user_id=user_id,
            name=requirements.get('name', 'Generated Workflow'),
            description=requirements.get('description', 'Auto-generated workflow'),
            steps=steps,
            config=config
        )
        
        return workflow
    
    async def _estimate_workflow_cost(self, workflow: Workflow) -> float:
        """Estimate workflow execution cost"""
        
        total_cost = 0.0
        
        for step in workflow.steps:
            # Get agent policy for cost estimation
            agent = await self.agent_registry.get_agent_by_id_and_version(step.agent_id)
            if agent:
                total_cost += agent.policy.cost_per_execution
        
        return total_cost
    
    async def _estimate_workflow_duration(self, workflow: Workflow) -> int:
        """Estimate workflow duration in minutes"""
        
        if workflow.config.execution_strategy == ExecutionStrategy.SEQUENTIAL:
            # Sum all step timeouts
            total_seconds = sum(step.timeout_seconds for step in workflow.steps)
        else:
            # For parallel, use maximum timeout
            total_seconds = max(step.timeout_seconds for step in workflow.steps) if workflow.steps else 0
        
        return max(1, total_seconds // 60)  # Convert to minutes, minimum 1
    
    async def _get_required_connections(self, workflow: Workflow) -> List[str]:
        """Get required connections for workflow"""
        
        required_connections = set()
        
        for step in workflow.steps:
            # Get agent to check required credentials
            agent = await self.agent_registry.get_agent_by_id_and_version(step.agent_id)
            if agent:
                # This would check agent.required_credentials
                # For now, infer from agent_id
                if 'email' in step.agent_id:
                    required_connections.add('gmail')
                elif 'whatsapp' in step.agent_id:
                    required_connections.add('whatsapp')
                elif 'telegram' in step.agent_id:
                    required_connections.add('telegram')
                elif 'supabase' in step.agent_id:
                    required_connections.add('supabase')
        
        return list(required_connections)
    
    async def _identify_workflow_risks(
        self, 
        workflow: Workflow, 
        requirements: Dict[str, Any]
    ) -> List[str]:
        """Identify potential risks in workflow execution"""
        
        risks = []
        
        # Check for rate limiting risks
        for step in workflow.steps:
            if 'email' in step.agent_id:
                risks.append("Rate limiting do Gmail pode afetar envio de emails em massa")
            elif 'whatsapp' in step.agent_id:
                risks.append("WhatsApp Business tem limites de mensagens por dia")
        
        # Check for dependency risks
        if len(workflow.steps) > 5:
            risks.append("Workflow complexo pode ter maior chance de falha")
        
        # Check for timeout risks
        total_timeout = sum(step.timeout_seconds for step in workflow.steps)
        if total_timeout > 1800:  # 30 minutes
            risks.append("Workflow longo pode exceder timeout")
        
        return risks
    
    async def _execute_workflow_steps(
        self, 
        workflow: Workflow, 
        execution: WorkflowExecution
    ) -> WorkflowExecution:
        """Execute workflow steps based on strategy"""
        
        if workflow.config.execution_strategy == ExecutionStrategy.SEQUENTIAL:
            return await self._execute_sequential(workflow, execution)
        elif workflow.config.execution_strategy == ExecutionStrategy.PARALLEL:
            return await self._execute_parallel(workflow, execution)
        else:
            # Default to sequential
            return await self._execute_sequential(workflow, execution)
    
    async def _execute_sequential(
        self, 
        workflow: Workflow, 
        execution: WorkflowExecution
    ) -> WorkflowExecution:
        """Execute steps sequentially"""
        
        completed_steps = []
        
        for step in workflow.steps:
            # Check dependencies
            if not step.can_execute(completed_steps):
                step.skip_execution("Dependencies not met")
                execution.add_log('warning', f'Step {step.step_id} skipped: dependencies not met')
                continue
            
            # Execute step
            try:
                execution.add_log('info', f'Starting step: {step.step_id}')
                step_result = await self._execute_single_step(step, execution.input_data)
                
                step.complete_execution(step_result, step_result.get('execution_time_ms', 0))
                execution.add_step_result(step.to_dict())
                execution.add_log('info', f'Step {step.step_id} completed successfully')
                
                completed_steps.append(step.step_id)
                
            except Exception as e:
                step.fail_execution(str(e), 0)
                execution.add_step_result(step.to_dict())
                execution.add_log('error', f'Step {step.step_id} failed: {str(e)}')
                
                # Handle failure based on strategy
                if workflow.config.failure_strategy == 'stop':
                    execution.fail_execution(f"Step {step.step_id} failed: {str(e)}")
                    break
        
        # Complete execution if all steps processed
        if execution.status == ExecutionStatus.RUNNING:
            execution.complete_execution(execution.results)
            execution.add_log('info', 'Workflow execution completed successfully')
        
        return execution
    
    async def _execute_parallel(
        self, 
        workflow: Workflow, 
        execution: WorkflowExecution
    ) -> WorkflowExecution:
        """Execute steps in parallel (simplified implementation)"""
        
        # For now, execute sequentially but log as parallel
        execution.add_log('info', 'Executing steps in parallel mode')
        return await self._execute_sequential(workflow, execution)
    
    async def _execute_single_step(
        self, 
        step: WorkflowStep, 
        global_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step"""
        
        # This would call the actual agent execution
        # For now, return mock result
        
        return {
            'step_id': step.step_id,
            'agent_id': step.agent_id,
            'action': step.action,
            'success': True,
            'output': {
                'message': f'Step {step.step_id} executed successfully',
                'data': step.input_data
            },
            'execution_time_ms': 1500
        }
    
    async def _dry_run_workflow(
        self, 
        workflow: Workflow, 
        execution: WorkflowExecution
    ) -> WorkflowExecution:
        """Execute workflow in dry-run mode"""
        
        execution.add_log('info', 'Starting dry-run execution')
        
        for step in workflow.steps:
            # Simulate step execution
            step_result = {
                'step_id': step.step_id,
                'agent_id': step.agent_id,
                'action': step.action,
                'success': True,
                'output': {'message': f'DRY RUN: Step {step.step_id} would execute successfully'},
                'execution_time_ms': 100
            }
            
            step.complete_execution(step_result, 100)
            execution.add_step_result(step.to_dict())
            execution.add_log('info', f'DRY RUN: Step {step.step_id} simulated')
        
        execution.complete_execution(execution.results)
        execution.add_log('info', 'Dry-run execution completed')
        
        return execution
    
    # Utility methods for conversation
    
    async def _generate_clarifying_questions(self, intent_analysis: Dict[str, Any]) -> List[str]:
        """Generate clarifying questions based on intent analysis"""
        
        questions = [
            "Pode me dar mais detalhes sobre o que você quer automatizar?",
            "Quais sistemas ou plataformas você quer integrar?",
            "Com que frequência isso deve ser executado?",
            "Há alguma condição específica para a execução?"
        ]
        
        return questions
    
    async def _generate_initial_workflow(
        self, 
        user_id: UUID, 
        intent_analysis: Dict[str, Any]
    ) -> Optional[CreateWorkflowSchema]:
        """Generate initial workflow suggestion"""
        
        primary_intent = intent_analysis['primary_intent']
        
        if primary_intent == 'send_email':
            return CreateWorkflowSchema(
                name="Email Automation Workflow",
                description="Workflow para envio automatizado de emails",
                steps=[{
                    'step_id': 'send_email_1',
                    'agent_id': 'sa-email-basic',
                    'action': 'send_email',
                    'input_data': {},
                    'depends_on': [],
                    'timeout_seconds': 60
                }]
            )
        
        return None
    
    async def _workflow_to_create_schema(self, workflow: Workflow) -> CreateWorkflowSchema:
        """Convert workflow domain object to create schema"""
        
        return CreateWorkflowSchema(
            name=workflow.name,
            description=workflow.description,
            steps=[{
                'step_id': step.step_id,
                'agent_id': step.agent_id,
                'agent_version': step.agent_version,
                'action': step.action,
                'input_data': step.input_data,
                'depends_on': step.depends_on,
                'timeout_seconds': step.timeout_seconds,
                'retry_count': step.retry_count,
                'condition': step.condition
            } for step in workflow.steps],
            config=workflow.config.to_dict()
        )
    
    async def _generate_plan_description(
        self, 
        requirements: Dict[str, Any], 
        workflow: Workflow
    ) -> str:
        """Generate human-readable plan description"""
        
        primary_intent = requirements.get('primary_intent', 'general')
        step_count = len(workflow.steps)
        
        descriptions = {
            'send_email': f"Enviar emails usando {step_count} passo(s)",
            'send_message': f"Enviar mensagens usando {step_count} passo(s)",
            'process_data': f"Processar dados usando {step_count} passo(s)",
            'integrate_system': f"Integrar sistemas usando {step_count} passo(s)"
        }
        
        return descriptions.get(primary_intent, f"Executar workflow com {step_count} passo(s)")
    
    # Entity extraction methods
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        # Brazilian phone patterns
        patterns = [
            r'\+55\s*\(?(\d{2})\)?\s*9?\s*(\d{4,5})-?(\d{4})',
            r'\(?(\d{2})\)?\s*9?\s*(\d{4,5})-?(\d{4})'
        ]
        
        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 3:
                    phones.append(f"+55{match[0]}{match[1]}{match[2]}")
        
        return phones
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        # Simple date patterns
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # DD/MM/YYYY
            r'\d{4}-\d{2}-\d{2}',      # YYYY-MM-DD
            r'\d{1,2} de \w+ de \d{4}' # DD de mês de YYYY
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text))
        
        return dates
    
    def _extract_numbers(self, text: str) -> List[float]:
        """Extract numbers from text"""
        number_pattern = r'\b\d+(?:\.\d+)?\b'
        matches = re.findall(number_pattern, text)
        return [float(match) for match in matches]    asy
nc def list_user_workflows(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Workflow]:
        """List workflows for a user"""
        return await self.workflow_repo.find_workflows_by_user(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
    
    async def get_workflow_by_id(self, workflow_id: UUID) -> Optional[Workflow]:
        """Get workflow by ID"""
        return await self.workflow_repo.find_workflow_by_id(workflow_id)
    
    async def get_workflow_run_by_id(self, run_id: UUID, user_id: UUID) -> Optional[WorkflowRun]:
        """Get workflow run by ID"""
        workflow_run = await self.workflow_repo.find_workflow_run_by_id(run_id)
        if workflow_run and workflow_run.user_id != user_id:
            raise ValueError("Usuário não tem permissão para ver esta execução")
        return workflow_run
    
    async def list_workflow_runs(
        self,
        user_id: UUID,
        workflow_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[WorkflowRun]:
        """List workflow runs for a user"""
        if workflow_id:
            return await self.workflow_repo.find_workflow_runs_by_workflow(
                workflow_id=workflow_id,
                status=status,
                limit=limit,
                offset=offset
            )
        else:
            # This would need a new repository method for user-based filtering
            # For now, return empty list
            return []
    
    async def process_chat_message(
        self,
        user_id: UUID,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process conversational message for workflow creation"""
        # This is a simplified implementation
        # In production, would use NLP/LLM for intent recognition
        
        context = context or {}
        
        # Simple keyword-based responses
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['criar', 'novo', 'workflow']):
            return {
                'message': 'Vou te ajudar a criar um novo workflow! Que tipo de automação você precisa?',
                'suggested_actions': [
                    'Enviar email',
                    'Consultar banco de dados',
                    'Enviar mensagem WhatsApp',
                    'Processar dados'
                ],
                'requires_confirmation': False,
                'context': {'state': 'gathering_requirements'}
            }
        
        elif any(word in message_lower for word in ['email', 'enviar']):
            return {
                'message': 'Entendi que você quer enviar emails. Para quem e com que conteúdo?',
                'suggested_actions': [
                    'Email simples',
                    'Email com anexo',
                    'Email em massa'
                ],
                'requires_confirmation': False,
                'context': {'state': 'configuring_email', 'agent_type': 'sa-email-basic'}
            }
        
        elif any(word in message_lower for word in ['executar', 'rodar']):
            # Check if user has workflows
            workflows = await self.list_user_workflows(user_id, limit=5)
            if workflows:
                workflow_names = [w.name for w in workflows[:3]]
                return {
                    'message': f'Você tem {len(workflows)} workflows disponíveis. Qual você quer executar?',
                    'suggested_actions': workflow_names,
                    'requires_confirmation': True,
                    'context': {'state': 'selecting_workflow', 'workflows': [str(w.id) for w in workflows[:3]]}
                }
            else:
                return {
                    'message': 'Você ainda não tem workflows criados. Quer criar um novo?',
                    'suggested_actions': ['Criar novo workflow'],
                    'requires_confirmation': False,
                    'context': {'state': 'no_workflows'}
                }
        
        else:
            return {
                'message': 'Como posso te ajudar? Posso criar workflows, executar automações ou responder dúvidas.',
                'suggested_actions': [
                    'Criar novo workflow',
                    'Executar workflow existente',
                    'Ver histórico de execuções'
                ],
                'requires_confirmation': False,
                'context': {'state': 'initial'}
            }
    
    async def get_execution_metrics(
        self,
        user_id: UUID,
        workflow_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get execution metrics and analytics"""
        # This would query the database for metrics
        # For now, return mock data
        
        return {
            'total_executions': 42,
            'successful_executions': 38,
            'failed_executions': 4,
            'success_rate': 90.48,
            'avg_execution_time_ms': 2500,
            'total_agents_used': 5,
            'most_used_agents': [
                {'agent_id': 'sa-email-basic', 'count': 25},
                {'agent_id': 'sa-database', 'count': 18},
                {'agent_id': 'sa-whatsapp', 'count': 12}
            ],
            'execution_trends': [
                {'date': '2024-01-01', 'executions': 5, 'success_rate': 100.0},
                {'date': '2024-01-02', 'executions': 8, 'success_rate': 87.5},
                {'date': '2024-01-03', 'executions': 12, 'success_rate': 91.7}
            ]
        }

def get_orchestrator_service() -> OrchestratorService:
    """Dependency injection for orchestrator service"""
    return OrchestratorService()