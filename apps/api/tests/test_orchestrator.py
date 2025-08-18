"""
Tests for Orchestrator Service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID
from datetime import datetime

from app.services.orchestrator_service import OrchestratorService
from app.domain.orchestrator import (
    Workflow, WorkflowRun, WorkflowStep, WorkflowConfig,
    ExecutionStrategy, FailureStrategy, WorkflowStatus, WorkflowRunStatus
)

class TestOrchestratorService:
    
    @pytest.fixture
    def mock_orchestrator_repo(self):
        """Mock orchestrator repository"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_agent_registry(self):
        """Mock agent registry service"""
        return AsyncMock()
    
    @pytest.fixture
    def orchestrator_service(self, mock_orchestrator_repo, mock_agent_registry):
        """Orchestrator service with mocked dependencies"""
        return OrchestratorService(
            orchestrator_repository=mock_orchestrator_repo,
            agent_registry_service=mock_agent_registry
        )
    
    @pytest.fixture
    def sample_workflow_data(self):
        """Sample workflow data for testing"""
        return {
            'name': 'Test Workflow',
            'description': 'A test workflow',
            'steps': [
                {
                    'step_id': 'step1',
                    'agent_id': 'sa-email-basic',
                    'agent_version': '1.0.0',
                    'action': 'send_email',
                    'input_data': {'to': 'test@example.com', 'subject': 'Test'},
                    'depends_on': [],
                    'timeout_seconds': 300,
                    'retry_count': 2
                },
                {
                    'step_id': 'step2',
                    'agent_id': 'sa-database',
                    'agent_version': '1.0.0',
                    'action': 'query',
                    'input_data': {'query': 'SELECT * FROM users'},
                    'depends_on': ['step1'],
                    'timeout_seconds': 180,
                    'retry_count': 1
                }
            ],
            'config': {
                'execution_strategy': 'sequential',
                'max_parallel_steps': 3,
                'failure_strategy': 'stop',
                'retry_policy': {'delay_seconds': 5},
                'timeout_minutes': 30
            }
        }
    
    @pytest.fixture
    def sample_workflow(self, sample_workflow_data):
        """Sample workflow domain object"""
        user_id = uuid4()
        
        # Create steps
        steps = []
        for step_data in sample_workflow_data['steps']:
            step = WorkflowStep(
                step_id=step_data['step_id'],
                agent_id=step_data['agent_id'],
                agent_version=step_data['agent_version'],
                action=step_data['action'],
                input_data=step_data['input_data'],
                depends_on=step_data['depends_on'],
                timeout_seconds=step_data['timeout_seconds'],
                retry_count=step_data['retry_count']
            )
            steps.append(step)
        
        # Create config
        config_data = sample_workflow_data['config']
        config = WorkflowConfig(
            execution_strategy=ExecutionStrategy(config_data['execution_strategy']),
            max_parallel_steps=config_data['max_parallel_steps'],
            failure_strategy=FailureStrategy(config_data['failure_strategy']),
            retry_policy=config_data['retry_policy'],
            timeout_minutes=config_data['timeout_minutes']
        )
        
        return Workflow(
            user_id=user_id,
            name=sample_workflow_data['name'],
            description=sample_workflow_data['description'],
            steps=steps,
            config=config
        )

    @pytest.mark.asyncio
    async def test_create_workflow_success(
        self, 
        orchestrator_service, 
        mock_orchestrator_repo,
        mock_agent_registry,
        sample_workflow_data
    ):
        """Test successful workflow creation"""
        # Arrange
        user_id = uuid4()
        
        # Mock agent registry to return valid agents
        mock_agent = MagicMock()
        mock_agent.has_capability.return_value = True
        mock_agent_registry.get_agent_by_id_and_version.return_value = mock_agent
        
        # Mock repository save
        expected_workflow = MagicMock()
        expected_workflow.id = uuid4()
        expected_workflow.name = sample_workflow_data['name']
        mock_orchestrator_repo.save_workflow.return_value = expected_workflow
        
        # Act
        result = await orchestrator_service.create_workflow(user_id, sample_workflow_data)
        
        # Assert
        assert result == expected_workflow
        mock_orchestrator_repo.save_workflow.assert_called_once()
        
        # Verify agent validation was called
        assert mock_agent_registry.get_agent_by_id_and_version.call_count == 2  # Two steps
    
    @pytest.mark.asyncio
    async def test_create_workflow_invalid_agent(
        self,
        orchestrator_service,
        mock_agent_registry,
        sample_workflow_data
    ):
        """Test workflow creation with invalid agent"""
        # Arrange
        user_id = uuid4()
        mock_agent_registry.get_agent_by_id_and_version.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="não encontrado"):
            await orchestrator_service.create_workflow(user_id, sample_workflow_data)
    
    @pytest.mark.asyncio
    async def test_create_workflow_missing_capability(
        self,
        orchestrator_service,
        mock_agent_registry,
        sample_workflow_data
    ):
        """Test workflow creation with agent missing capability"""
        # Arrange
        user_id = uuid4()
        mock_agent = MagicMock()
        mock_agent.has_capability.return_value = False
        mock_agent_registry.get_agent_by_id_and_version.return_value = mock_agent
        
        # Act & Assert
        with pytest.raises(ValueError, match="não tem capacidade"):
            await orchestrator_service.create_workflow(user_id, sample_workflow_data)
    
    @pytest.mark.asyncio
    async def test_execute_workflow_success(
        self,
        orchestrator_service,
        mock_orchestrator_repo,
        mock_agent_registry,
        sample_workflow
    ):
        """Test successful workflow execution"""
        # Arrange
        user_id = sample_workflow.user_id
        workflow_id = sample_workflow.id
        
        # Mock repository methods
        mock_orchestrator_repo.find_workflow_by_id.return_value = sample_workflow
        mock_orchestrator_repo.save_workflow_run.return_value = MagicMock()
        
        # Mock agent registry
        mock_agent = MagicMock()
        mock_agent.has_capability.return_value = True
        mock_agent_registry.get_agent_by_id_and_version.return_value = mock_agent
        
        # Act
        result = await orchestrator_service.execute_workflow(
            workflow_id=workflow_id,
            user_id=user_id,
            input_data={'test': 'data'}
        )
        
        # Assert
        assert result is not None
        assert result.workflow_id == workflow_id
        assert result.user_id == user_id
        assert result.status == WorkflowRunStatus.PENDING
        mock_orchestrator_repo.save_workflow_run.assert_called()
    
    @pytest.mark.asyncio
    async def test_execute_workflow_not_found(
        self,
        orchestrator_service,
        mock_orchestrator_repo
    ):
        """Test workflow execution with non-existent workflow"""
        # Arrange
        workflow_id = uuid4()
        user_id = uuid4()
        mock_orchestrator_repo.find_workflow_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="não encontrado"):
            await orchestrator_service.execute_workflow(workflow_id, user_id)
    
    @pytest.mark.asyncio
    async def test_execute_workflow_unauthorized(
        self,
        orchestrator_service,
        mock_orchestrator_repo,
        sample_workflow
    ):
        """Test workflow execution by unauthorized user"""
        # Arrange
        workflow_id = sample_workflow.id
        unauthorized_user_id = uuid4()  # Different from workflow owner
        mock_orchestrator_repo.find_workflow_by_id.return_value = sample_workflow
        
        # Act & Assert
        with pytest.raises(ValueError, match="não tem permissão"):
            await orchestrator_service.execute_workflow(workflow_id, unauthorized_user_id)
    
    @pytest.mark.asyncio
    async def test_execute_workflow_dry_run(
        self,
        orchestrator_service,
        mock_orchestrator_repo,
        sample_workflow
    ):
        """Test workflow dry run execution"""
        # Arrange
        user_id = sample_workflow.user_id
        workflow_id = sample_workflow.id
        
        mock_orchestrator_repo.find_workflow_by_id.return_value = sample_workflow
        
        # Mock save to return the run with completed status
        def mock_save(workflow_run):
            workflow_run.status = WorkflowRunStatus.COMPLETED
            return workflow_run
        
        mock_orchestrator_repo.save_workflow_run.side_effect = mock_save
        
        # Act
        result = await orchestrator_service.execute_workflow(
            workflow_id=workflow_id,
            user_id=user_id,
            dry_run=True
        )
        
        # Assert
        assert result.status == WorkflowRunStatus.COMPLETED
        # Should have log about dry run
        assert any('dry run' in log.message.lower() for log in result.execution_logs)
    
    @pytest.mark.asyncio
    async def test_cancel_workflow_run(
        self,
        orchestrator_service,
        mock_orchestrator_repo
    ):
        """Test workflow run cancellation"""
        # Arrange
        run_id = uuid4()
        user_id = uuid4()
        
        # Create mock workflow run
        mock_run = MagicMock()
        mock_run.id = run_id
        mock_run.user_id = user_id
        mock_run.status = WorkflowRunStatus.RUNNING
        mock_run.cancel = MagicMock()
        
        mock_orchestrator_repo.find_workflow_run_by_id.return_value = mock_run
        mock_orchestrator_repo.save_workflow_run.return_value = mock_run
        
        # Act
        result = await orchestrator_service.cancel_workflow_run(run_id, user_id)
        
        # Assert
        assert result == mock_run
        mock_run.cancel.assert_called_once()
        mock_orchestrator_repo.save_workflow_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_workflow_run_not_found(
        self,
        orchestrator_service,
        mock_orchestrator_repo
    ):
        """Test cancelling non-existent workflow run"""
        # Arrange
        run_id = uuid4()
        user_id = uuid4()
        mock_orchestrator_repo.find_workflow_run_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="não encontrada"):
            await orchestrator_service.cancel_workflow_run(run_id, user_id)
    
    @pytest.mark.asyncio
    async def test_cancel_workflow_run_unauthorized(
        self,
        orchestrator_service,
        mock_orchestrator_repo
    ):
        """Test cancelling workflow run by unauthorized user"""
        # Arrange
        run_id = uuid4()
        user_id = uuid4()
        unauthorized_user_id = uuid4()
        
        mock_run = MagicMock()
        mock_run.user_id = user_id  # Different from unauthorized_user_id
        mock_orchestrator_repo.find_workflow_run_by_id.return_value = mock_run
        
        # Act & Assert
        with pytest.raises(ValueError, match="não tem permissão"):
            await orchestrator_service.cancel_workflow_run(run_id, unauthorized_user_id)
    
    @pytest.mark.asyncio
    async def test_get_workflow_run_status(
        self,
        orchestrator_service,
        mock_orchestrator_repo
    ):
        """Test getting workflow run status"""
        # Arrange
        run_id = uuid4()
        user_id = uuid4()
        
        # Create mock workflow run with results
        mock_run = MagicMock()
        mock_run.id = run_id
        mock_run.user_id = user_id
        mock_run.workflow_id = uuid4()
        mock_run.status = WorkflowRunStatus.COMPLETED
        mock_run.results = [MagicMock(), MagicMock()]  # 2 results
        mock_run.results[0].status = 'completed'
        mock_run.results[1].status = 'completed'
        mock_run.results[0].to_dict.return_value = {'step_id': 'step1', 'status': 'completed'}
        mock_run.results[1].to_dict.return_value = {'step_id': 'step2', 'status': 'completed'}
        mock_run.execution_logs = [MagicMock() for _ in range(15)]  # More than 10 logs
        for log in mock_run.execution_logs:
            log.to_dict.return_value = {'level': 'info', 'message': 'test'}
        mock_run.started_at = datetime.utcnow()
        mock_run.completed_at = datetime.utcnow()
        mock_run.calculate_execution_time.return_value = 5000
        mock_run.get_success_rate.return_value = 100.0
        
        mock_orchestrator_repo.find_workflow_run_by_id.return_value = mock_run
        
        # Act
        result = await orchestrator_service.get_workflow_run_status(run_id, user_id)
        
        # Assert
        assert result['run_id'] == str(run_id)
        assert result['status'] == 'completed'
        assert result['progress']['total_steps'] == 2
        assert result['progress']['completed_steps'] == 2
        assert result['progress']['success_rate'] == 100.0
        assert len(result['logs']) == 10  # Should be limited to last 10
        assert result['timing']['execution_time_ms'] == 5000
    
    @pytest.mark.asyncio
    async def test_get_active_runs(
        self,
        orchestrator_service
    ):
        """Test getting active workflow runs"""
        # Arrange
        run_id = uuid4()
        workflow_id = uuid4()
        user_id = uuid4()
        
        # Add mock active run
        mock_run = MagicMock()
        mock_run.id = run_id
        mock_run.workflow_id = workflow_id
        mock_run.user_id = user_id
        mock_run.status = WorkflowRunStatus.RUNNING
        
        orchestrator_service._active_runs = {
            run_id: {
                'workflow': MagicMock(),
                'run': mock_run,
                'started_at': datetime.utcnow()
            }
        }
        
        # Act
        result = await orchestrator_service.get_active_runs()
        
        # Assert
        assert len(result) == 1
        assert result[0]['run_id'] == str(run_id)
        assert result[0]['workflow_id'] == str(workflow_id)
        assert result[0]['status'] == 'running'
        assert 'running_time_ms' in result[0]

class TestWorkflowDomain:
    
    def test_workflow_creation_success(self):
        """Test successful workflow creation"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(
                step_id='step1',
                agent_id='sa-email',
                action='send_email',
                input_data={'to': 'test@example.com'}
            )
        ]
        
        # Act
        workflow = Workflow(
            user_id=user_id,
            name='Test Workflow',
            steps=steps
        )
        
        # Assert
        assert workflow.user_id == user_id
        assert workflow.name == 'Test Workflow'
        assert len(workflow.steps) == 1
        assert workflow.status == WorkflowStatus.DRAFT
        assert 'sa-email' in workflow.agents_used
    
    def test_workflow_validation_empty_steps(self):
        """Test workflow validation with empty steps"""
        # Arrange
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(ValueError, match="pelo menos um passo"):
            Workflow(
                user_id=user_id,
                name='Test Workflow',
                steps=[]
            )
    
    def test_workflow_validation_empty_name(self):
        """Test workflow validation with empty name"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(
                step_id='step1',
                agent_id='sa-email',
                action='send_email'
            )
        ]
        
        # Act & Assert
        with pytest.raises(ValueError, match="Nome do workflow é obrigatório"):
            Workflow(
                user_id=user_id,
                name='   ',  # Empty after strip
                steps=steps
            )
    
    def test_workflow_validation_duplicate_step_ids(self):
        """Test workflow validation with duplicate step IDs"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(step_id='step1', agent_id='sa-email', action='send_email'),
            WorkflowStep(step_id='step1', agent_id='sa-database', action='query')  # Duplicate ID
        ]
        
        # Act & Assert
        with pytest.raises(ValueError, match="IDs dos passos devem ser únicos"):
            Workflow(
                user_id=user_id,
                name='Test Workflow',
                steps=steps
            )
    
    def test_workflow_validation_invalid_dependency(self):
        """Test workflow validation with invalid dependency"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(
                step_id='step1',
                agent_id='sa-email',
                action='send_email',
                depends_on=['nonexistent_step']  # Invalid dependency
            )
        ]
        
        # Act & Assert
        with pytest.raises(ValueError, match="Dependência 'nonexistent_step' não encontrada"):
            Workflow(
                user_id=user_id,
                name='Test Workflow',
                steps=steps
            )
    
    def test_workflow_get_execution_order_sequential(self):
        """Test execution order for sequential strategy"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(step_id='step1', agent_id='sa-email', action='send_email'),
            WorkflowStep(step_id='step2', agent_id='sa-database', action='query', depends_on=['step1'])
        ]
        config = WorkflowConfig(execution_strategy=ExecutionStrategy.SEQUENTIAL)
        
        workflow = Workflow(
            user_id=user_id,
            name='Test Workflow',
            steps=steps,
            config=config
        )
        
        # Act
        execution_order = workflow.get_execution_order()
        
        # Assert
        assert len(execution_order) == 2
        assert execution_order[0] == ['step1']
        assert execution_order[1] == ['step2']
    
    def test_workflow_get_execution_order_parallel(self):
        """Test execution order for parallel strategy"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(step_id='step1', agent_id='sa-email', action='send_email'),
            WorkflowStep(step_id='step2', agent_id='sa-sms', action='send_sms'),
            WorkflowStep(step_id='step3', agent_id='sa-database', action='query', depends_on=['step1', 'step2'])
        ]
        config = WorkflowConfig(execution_strategy=ExecutionStrategy.PARALLEL)
        
        workflow = Workflow(
            user_id=user_id,
            name='Test Workflow',
            steps=steps,
            config=config
        )
        
        # Act
        execution_order = workflow.get_execution_order()
        
        # Assert
        assert len(execution_order) == 2
        # First level should have independent steps
        assert set(execution_order[0]) == {'step1', 'step2'}
        # Second level should have dependent step
        assert execution_order[1] == ['step3']
    
    def test_workflow_add_step_success(self):
        """Test adding step to workflow"""
        # Arrange
        user_id = uuid4()
        initial_step = WorkflowStep(step_id='step1', agent_id='sa-email', action='send_email')
        workflow = Workflow(
            user_id=user_id,
            name='Test Workflow',
            steps=[initial_step]
        )
        
        new_step = WorkflowStep(step_id='step2', agent_id='sa-database', action='query')
        
        # Act
        workflow.add_step(new_step)
        
        # Assert
        assert len(workflow.steps) == 2
        assert 'sa-database' in workflow.agents_used
    
    def test_workflow_add_step_duplicate_id(self):
        """Test adding step with duplicate ID"""
        # Arrange
        user_id = uuid4()
        initial_step = WorkflowStep(step_id='step1', agent_id='sa-email', action='send_email')
        workflow = Workflow(
            user_id=user_id,
            name='Test Workflow',
            steps=[initial_step]
        )
        
        duplicate_step = WorkflowStep(step_id='step1', agent_id='sa-database', action='query')
        
        # Act & Assert
        with pytest.raises(ValueError, match="já existe"):
            workflow.add_step(duplicate_step)
    
    def test_workflow_remove_step_success(self):
        """Test removing step from workflow"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(step_id='step1', agent_id='sa-email', action='send_email'),
            WorkflowStep(step_id='step2', agent_id='sa-database', action='query')
        ]
        workflow = Workflow(
            user_id=user_id,
            name='Test Workflow',
            steps=steps
        )
        
        # Act
        workflow.remove_step('step2')
        
        # Assert
        assert len(workflow.steps) == 1
        assert workflow.steps[0].step_id == 'step1'
    
    def test_workflow_remove_step_with_dependencies(self):
        """Test removing step that has dependencies"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(step_id='step1', agent_id='sa-email', action='send_email'),
            WorkflowStep(step_id='step2', agent_id='sa-database', action='query', depends_on=['step1'])
        ]
        workflow = Workflow(
            user_id=user_id,
            name='Test Workflow',
            steps=steps
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Passos dependentes"):
            workflow.remove_step('step1')
    
    def test_workflow_estimate_execution_time_sequential(self):
        """Test execution time estimation for sequential workflow"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(step_id='step1', agent_id='sa-email', action='send_email', timeout_seconds=300),
            WorkflowStep(step_id='step2', agent_id='sa-database', action='query', timeout_seconds=180)
        ]
        config = WorkflowConfig(execution_strategy=ExecutionStrategy.SEQUENTIAL)
        
        workflow = Workflow(
            user_id=user_id,
            name='Test Workflow',
            steps=steps,
            config=config
        )
        
        # Act
        estimated_time = workflow.estimate_execution_time()
        
        # Assert
        assert estimated_time == 480  # 300 + 180
    
    def test_workflow_estimate_execution_time_parallel(self):
        """Test execution time estimation for parallel workflow"""
        # Arrange
        user_id = uuid4()
        steps = [
            WorkflowStep(step_id='step1', agent_id='sa-email', action='send_email', timeout_seconds=300),
            WorkflowStep(step_id='step2', agent_id='sa-sms', action='send_sms', timeout_seconds=180),
            WorkflowStep(step_id='step3', agent_id='sa-database', action='query', timeout_seconds=240, depends_on=['step1', 'step2'])
        ]
        config = WorkflowConfig(execution_strategy=ExecutionStrategy.PARALLEL)
        
        workflow = Workflow(
            user_id=user_id,
            name='Test Workflow',
            steps=steps,
            config=config
        )
        
        # Act
        estimated_time = workflow.estimate_execution_time()
        
        # Assert
        # First level: max(300, 180) = 300
        # Second level: 240
        # Total: 300 + 240 = 540
        assert estimated_time == 540

class TestWorkflowRun:
    
    def test_workflow_run_creation(self):
        """Test workflow run creation"""
        # Arrange
        workflow_id = uuid4()
        user_id = uuid4()
        input_data = {'test': 'data'}
        
        # Act
        workflow_run = WorkflowRun(
            workflow_id=workflow_id,
            user_id=user_id,
            input_data=input_data
        )
        
        # Assert
        assert workflow_run.workflow_id == workflow_id
        assert workflow_run.user_id == user_id
        assert workflow_run.input_data == input_data
        assert workflow_run.status == WorkflowRunStatus.PENDING
        assert workflow_run.results == []
        assert workflow_run.execution_logs == []
    
    def test_workflow_run_start(self):
        """Test starting workflow run"""
        # Arrange
        workflow_run = WorkflowRun(
            workflow_id=uuid4(),
            user_id=uuid4()
        )
        
        # Act
        workflow_run.start()
        
        # Assert
        assert workflow_run.status == WorkflowRunStatus.RUNNING
        assert workflow_run.started_at is not None
        assert len(workflow_run.execution_logs) == 1
        assert 'iniciada' in workflow_run.execution_logs[0].message.lower()
    
    def test_workflow_run_start_invalid_status(self):
        """Test starting workflow run with invalid status"""
        # Arrange
        workflow_run = WorkflowRun(
            workflow_id=uuid4(),
            user_id=uuid4(),
            status=WorkflowRunStatus.COMPLETED
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="não pode ser iniciada"):
            workflow_run.start()
    
    def test_workflow_run_complete(self):
        """Test completing workflow run"""
        # Arrange
        workflow_run = WorkflowRun(
            workflow_id=uuid4(),
            user_id=uuid4(),
            status=WorkflowRunStatus.RUNNING
        )
        
        # Act
        workflow_run.complete()
        
        # Assert
        assert workflow_run.status == WorkflowRunStatus.COMPLETED
        assert workflow_run.completed_at is not None
        assert any('completada' in log.message.lower() for log in workflow_run.execution_logs)
    
    def test_workflow_run_fail(self):
        """Test failing workflow run"""
        # Arrange
        workflow_run = WorkflowRun(
            workflow_id=uuid4(),
            user_id=uuid4(),
            status=WorkflowRunStatus.RUNNING
        )
        error_message = "Something went wrong"
        
        # Act
        workflow_run.fail(error_message)
        
        # Assert
        assert workflow_run.status == WorkflowRunStatus.FAILED
        assert workflow_run.error_message == error_message
        assert workflow_run.completed_at is not None
        assert any('falhou' in log.message.lower() for log in workflow_run.execution_logs)
    
    def test_workflow_run_cancel(self):
        """Test cancelling workflow run"""
        # Arrange
        workflow_run = WorkflowRun(
            workflow_id=uuid4(),
            user_id=uuid4(),
            status=WorkflowRunStatus.RUNNING
        )
        
        # Act
        workflow_run.cancel()
        
        # Assert
        assert workflow_run.status == WorkflowRunStatus.CANCELLED
        assert workflow_run.completed_at is not None
        assert any('cancelada' in log.message.lower() for log in workflow_run.execution_logs)
    
    def test_workflow_run_cancel_invalid_status(self):
        """Test cancelling workflow run with invalid status"""
        # Arrange
        workflow_run = WorkflowRun(
            workflow_id=uuid4(),
            user_id=uuid4(),
            status=WorkflowRunStatus.COMPLETED
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="não pode ser cancelada"):
            workflow_run.cancel()
    
    def test_workflow_run_calculate_execution_time(self):
        """Test calculating execution time"""
        # Arrange
        workflow_run = WorkflowRun(
            workflow_id=uuid4(),
            user_id=uuid4()
        )
        
        # Simulate execution
        start_time = datetime.utcnow()
        workflow_run.started_at = start_time
        workflow_run.completed_at = start_time.replace(microsecond=start_time.microsecond + 500000)  # Add 0.5 seconds
        
        # Act
        execution_time = workflow_run.calculate_execution_time()
        
        # Assert
        assert execution_time >= 500  # At least 500ms
        assert execution_time < 1000   # Less than 1000ms
    
    def test_workflow_run_get_success_rate(self):
        """Test calculating success rate"""
        # Arrange
        from app.domain.orchestrator import WorkflowStepResult
        
        workflow_run = WorkflowRun(
            workflow_id=uuid4(),
            user_id=uuid4()
        )
        
        # Add some results
        workflow_run.results = [
            WorkflowStepResult(
                step_id='step1',
                agent_id='sa-email',
                status='completed',
                input_data={}
            ),
            WorkflowStepResult(
                step_id='step2',
                agent_id='sa-database',
                status='completed',
                input_data={}
            ),
            WorkflowStepResult(
                step_id='step3',
                agent_id='sa-sms',
                status='failed',
                input_data={}
            )
        ]
        
        # Act
        success_rate = workflow_run.get_success_rate()
        
        # Assert
        assert success_rate == 66.66666666666666  # 2/3 * 100