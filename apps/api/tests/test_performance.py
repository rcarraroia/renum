"""
Performance Tests
High-load scenario testing for the Renum API
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
import statistics

from app.main import app

client = TestClient(app)

class TestAPIPerformance:
    """Performance tests for API endpoints"""
    
    @pytest.fixture
    def mock_auth_token(self):
        """Mock authentication token"""
        return "valid-performance-test-token"
    
    @pytest.fixture
    def auth_headers(self, mock_auth_token):
        """Headers with authentication token"""
        return {"Authorization": f"Bearer {mock_auth_token}"}
    
    def test_health_endpoint_performance(self):
        """Test health endpoint performance under load"""
        num_requests = 100
        response_times = []
        
        for _ in range(num_requests):
            start_time = time.time()
            response = client.get("/health")
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append((end_time - start_time) * 1000)  # Convert to ms
        
        # Performance assertions
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        max_response_time = max(response_times)
        
        print(f"Health endpoint performance:")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  95th percentile: {p95_response_time:.2f}ms")
        print(f"  Max response time: {max_response_time:.2f}ms")
        
        # Performance thresholds
        assert avg_response_time < 50, f"Average response time too high: {avg_response_time:.2f}ms"
        assert p95_response_time < 100, f"95th percentile too high: {p95_response_time:.2f}ms"
        assert max_response_time < 200, f"Max response time too high: {max_response_time:.2f}ms"
    
    def test_concurrent_health_requests(self):
        """Test health endpoint with concurrent requests"""
        num_threads = 10
        requests_per_thread = 20
        
        def make_requests():
            response_times = []
            for _ in range(requests_per_thread):
                start_time = time.time()
                response = client.get("/health")
                end_time = time.time()
                
                assert response.status_code == 200
                response_times.append((end_time - start_time) * 1000)
            return response_times
        
        # Execute concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_requests) for _ in range(num_threads)]
            all_response_times = []
            for future in futures:
                all_response_times.extend(future.result())
        end_time = time.time()
        
        total_requests = num_threads * requests_per_thread
        total_time = end_time - start_time
        requests_per_second = total_requests / total_time
        
        avg_response_time = statistics.mean(all_response_times)
        p95_response_time = statistics.quantiles(all_response_times, n=20)[18]
        
        print(f"Concurrent health endpoint performance:")
        print(f"  Total requests: {total_requests}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Requests per second: {requests_per_second:.2f}")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  95th percentile: {p95_response_time:.2f}ms")
        
        # Performance assertions
        assert requests_per_second > 100, f"RPS too low: {requests_per_second:.2f}"
        assert avg_response_time < 100, f"Average response time too high: {avg_response_time:.2f}ms"
        assert p95_response_time < 200, f"95th percentile too high: {p95_response_time:.2f}ms"
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_agent_execution_performance(self, mock_get_user, auth_headers):
        """Test agent execution endpoint performance"""
        mock_get_user.return_value = {'user_id': 'perf-test-user', 'role': 'user'}
        
        execution_data = {
            "agent_id": "sa-http-generic",
            "capability": "http_request",
            "input_data": {
                "method": "GET",
                "url": "https://httpbin.org/get",
                "timeout": 5
            }
        }
        
        num_requests = 50
        response_times = []
        successful_requests = 0
        
        with patch('app.api.v1.agents.get_agent_by_id') as mock_get_agent:
            # Mock agent
            mock_agent = MagicMock()
            mock_agent.execute_capability.return_value = MagicMock(
                success=True,
                data={'status': 'success'},
                execution_time_ms=100
            )
            mock_get_agent.return_value = mock_agent
            
            for _ in range(num_requests):
                start_time = time.time()
                response = client.post(
                    "/api/v1/agents/execute",
                    json=execution_data,
                    headers=auth_headers
                )
                end_time = time.time()
                
                if response.status_code == 200:
                    successful_requests += 1
                
                response_times.append((end_time - start_time) * 1000)
        
        success_rate = (successful_requests / num_requests) * 100
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        
        print(f"Agent execution performance:")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  95th percentile: {p95_response_time:.2f}ms")
        
        # Performance assertions
        assert success_rate >= 95, f"Success rate too low: {success_rate:.1f}%"
        assert avg_response_time < 500, f"Average response time too high: {avg_response_time:.2f}ms"
        assert p95_response_time < 1000, f"95th percentile too high: {p95_response_time:.2f}ms"
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_orchestrator_performance(self, mock_get_user, auth_headers):
        """Test orchestrator endpoint performance"""
        mock_get_user.return_value = {'user_id': 'perf-test-user', 'role': 'user'}
        
        workflow_data = {
            "workflow_name": "Performance Test Workflow",
            "strategy": "sequential",
            "agents": [
                {
                    "agent_id": "sa-http-generic",
                    "capability": "http_request",
                    "input_data": {
                        "method": "GET",
                        "url": "https://httpbin.org/get"
                    }
                }
            ]
        }
        
        num_requests = 20  # Lower number for orchestrator tests
        response_times = []
        successful_requests = 0
        
        with patch('app.api.v1.orchestrator.orchestrator_service') as mock_service:
            mock_service.execute_workflow.return_value = {
                'execution_id': 'test-execution',
                'status': 'completed',
                'results': [{'success': True}]
            }
            
            for _ in range(num_requests):
                start_time = time.time()
                response = client.post(
                    "/api/v1/orchestrator/execute",
                    json=workflow_data,
                    headers=auth_headers
                )
                end_time = time.time()
                
                if response.status_code == 200:
                    successful_requests += 1
                
                response_times.append((end_time - start_time) * 1000)
        
        success_rate = (successful_requests / num_requests) * 100
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
        
        print(f"Orchestrator performance:")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  95th percentile: {p95_response_time:.2f}ms")
        
        # Performance assertions (more lenient for orchestrator)
        assert success_rate >= 90, f"Success rate too low: {success_rate:.1f}%"
        assert avg_response_time < 2000, f"Average response time too high: {avg_response_time:.2f}ms"
        assert p95_response_time < 5000, f"95th percentile too high: {p95_response_time:.2f}ms"

class TestMemoryPerformance:
    """Memory usage and leak tests"""
    
    def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests
        num_requests = 200
        for i in range(num_requests):
            response = client.get("/health")
            assert response.status_code == 200
            
            # Force garbage collection every 50 requests
            if i % 50 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        
        # Memory should not increase by more than 50MB
        assert memory_increase < 50, f"Memory increase too high: {memory_increase:.2f} MB"
    
    def test_no_memory_leaks_in_agent_execution(self):
        """Test for memory leaks in agent execution"""
        import psutil
        import gc
        
        process = psutil.Process()
        
        # Baseline memory measurement
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'memory-test-user', 'role': 'user'}
            
            with patch('app.api.v1.agents.get_agent_by_id') as mock_get_agent:
                mock_agent = MagicMock()
                mock_agent.execute_capability.return_value = MagicMock(
                    success=True,
                    data={'test': 'data'},
                    execution_time_ms=50
                )
                mock_get_agent.return_value = mock_agent
                
                # Execute many agent calls
                for i in range(100):
                    response = client.post(
                        "/api/v1/agents/execute",
                        json={
                            "agent_id": "sa-http-generic",
                            "capability": "http_request",
                            "input_data": {"method": "GET", "url": "https://httpbin.org/get"}
                        },
                        headers={"Authorization": "Bearer test-token"}
                    )
                    
                    if i % 25 == 0:
                        gc.collect()
        
        # Final memory measurement
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - baseline_memory
        
        print(f"Agent execution memory test:")
        print(f"  Baseline: {baseline_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        
        # Memory increase should be minimal
        assert memory_increase < 30, f"Potential memory leak detected: {memory_increase:.2f} MB increase"

class TestDatabasePerformance:
    """Database performance tests"""
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_credential_operations_performance(self, mock_get_user):
        """Test credential CRUD operations performance"""
        mock_get_user.return_value = {'user_id': 'db-perf-test-user', 'role': 'user'}
        
        headers = {"Authorization": "Bearer test-token"}
        
        # Test credential creation performance
        create_times = []
        credential_ids = []
        
        with patch('app.api.v1.credentials.user_credentials_service') as mock_service:
            mock_service.create_credential.return_value = 'test-credential-id'
            mock_service.get_user_credentials.return_value = []
            mock_service.get_credential.return_value = {
                'id': 'test-credential-id',
                'name': 'Test Credential',
                'provider': 'custom_api'
            }
            mock_service.delete_credential.return_value = True
            
            # Create credentials
            for i in range(50):
                credential_data = {
                    "name": f"Test Credential {i}",
                    "provider": "custom_api",
                    "credentials": {"api_key": f"test-key-{i}"}
                }
                
                start_time = time.time()
                response = client.post(
                    "/api/v1/credentials",
                    json=credential_data,
                    headers=headers
                )
                end_time = time.time()
                
                assert response.status_code == 200
                create_times.append((end_time - start_time) * 1000)
                credential_ids.append(f'test-credential-{i}')
            
            # Test credential retrieval performance
            read_times = []
            for _ in range(50):
                start_time = time.time()
                response = client.get("/api/v1/credentials", headers=headers)
                end_time = time.time()
                
                assert response.status_code == 200
                read_times.append((end_time - start_time) * 1000)
            
            # Test credential deletion performance
            delete_times = []
            for cred_id in credential_ids[:10]:  # Delete first 10
                start_time = time.time()
                response = client.delete(f"/api/v1/credentials/{cred_id}", headers=headers)
                end_time = time.time()
                
                delete_times.append((end_time - start_time) * 1000)
        
        # Performance analysis
        avg_create_time = statistics.mean(create_times)
        avg_read_time = statistics.mean(read_times)
        avg_delete_time = statistics.mean(delete_times)
        
        print(f"Credential operations performance:")
        print(f"  Average create time: {avg_create_time:.2f}ms")
        print(f"  Average read time: {avg_read_time:.2f}ms")
        print(f"  Average delete time: {avg_delete_time:.2f}ms")
        
        # Performance assertions
        assert avg_create_time < 200, f"Create operation too slow: {avg_create_time:.2f}ms"
        assert avg_read_time < 100, f"Read operation too slow: {avg_read_time:.2f}ms"
        assert avg_delete_time < 150, f"Delete operation too slow: {avg_delete_time:.2f}ms"

class TestRateLimitingPerformance:
    """Rate limiting performance tests"""
    
    def test_rate_limiting_overhead(self):
        """Test performance overhead of rate limiting middleware"""
        # Test without rate limiting (health endpoint)
        num_requests = 100
        
        # Measure baseline performance
        baseline_times = []
        for _ in range(num_requests):
            start_time = time.time()
            response = client.get("/health")  # Health endpoint bypasses rate limiting
            end_time = time.time()
            
            assert response.status_code == 200
            baseline_times.append((end_time - start_time) * 1000)
        
        # Measure with rate limiting (other endpoints)
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'rate-limit-test-user', 'role': 'user'}
            
            rate_limited_times = []
            for _ in range(num_requests):
                start_time = time.time()
                response = client.get(
                    "/api/v1/analytics/dashboard",
                    headers={"Authorization": "Bearer test-token"}
                )
                end_time = time.time()
                
                # May get rate limited, but measure time anyway
                rate_limited_times.append((end_time - start_time) * 1000)
        
        baseline_avg = statistics.mean(baseline_times)
        rate_limited_avg = statistics.mean(rate_limited_times)
        overhead = rate_limited_avg - baseline_avg
        overhead_percent = (overhead / baseline_avg) * 100
        
        print(f"Rate limiting overhead:")
        print(f"  Baseline average: {baseline_avg:.2f}ms")
        print(f"  Rate limited average: {rate_limited_avg:.2f}ms")
        print(f"  Overhead: {overhead:.2f}ms ({overhead_percent:.1f}%)")
        
        # Rate limiting overhead should be minimal
        assert overhead_percent < 50, f"Rate limiting overhead too high: {overhead_percent:.1f}%"

class TestWebSocketPerformance:
    """WebSocket performance tests"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_performance(self):
        """Test WebSocket connection establishment performance"""
        from fastapi.testclient import TestClient
        
        connection_times = []
        num_connections = 20
        
        for _ in range(num_connections):
            start_time = time.time()
            
            try:
                with client.websocket_connect("/api/v1/ws") as websocket:
                    end_time = time.time()
                    connection_times.append((end_time - start_time) * 1000)
                    
                    # Send a test message
                    websocket.send_json({"type": "ping"})
                    response = websocket.receive_json()
                    
            except Exception as e:
                # Connection might fail in test environment
                print(f"WebSocket connection failed: {e}")
                connection_times.append(1000)  # Default high time for failed connections
        
        if connection_times:
            avg_connection_time = statistics.mean(connection_times)
            max_connection_time = max(connection_times)
            
            print(f"WebSocket performance:")
            print(f"  Average connection time: {avg_connection_time:.2f}ms")
            print(f"  Max connection time: {max_connection_time:.2f}ms")
            
            # Performance assertions (lenient for test environment)
            assert avg_connection_time < 1000, f"WebSocket connection too slow: {avg_connection_time:.2f}ms"

@pytest.mark.slow
class TestStressTests:
    """Stress tests for extreme load scenarios"""
    
    def test_extreme_concurrent_load(self):
        """Test API under extreme concurrent load"""
        num_threads = 20
        requests_per_thread = 50
        
        def stress_test_worker():
            response_times = []
            errors = 0
            
            for _ in range(requests_per_thread):
                try:
                    start_time = time.time()
                    response = client.get("/health")
                    end_time = time.time()
                    
                    response_times.append((end_time - start_time) * 1000)
                    
                    if response.status_code != 200:
                        errors += 1
                        
                except Exception:
                    errors += 1
                    response_times.append(5000)  # 5 second timeout
            
            return response_times, errors
        
        # Execute stress test
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(stress_test_worker) for _ in range(num_threads)]
            
            all_response_times = []
            total_errors = 0
            
            for future in futures:
                response_times, errors = future.result()
                all_response_times.extend(response_times)
                total_errors += errors
        
        end_time = time.time()
        
        total_requests = num_threads * requests_per_thread
        total_time = end_time - start_time
        requests_per_second = total_requests / total_time
        error_rate = (total_errors / total_requests) * 100
        
        avg_response_time = statistics.mean(all_response_times)
        p95_response_time = statistics.quantiles(all_response_times, n=20)[18]
        p99_response_time = statistics.quantiles(all_response_times, n=100)[98]
        
        print(f"Stress test results:")
        print(f"  Total requests: {total_requests}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Requests per second: {requests_per_second:.2f}")
        print(f"  Error rate: {error_rate:.2f}%")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  95th percentile: {p95_response_time:.2f}ms")
        print(f"  99th percentile: {p99_response_time:.2f}ms")
        
        # Stress test assertions (more lenient)
        assert error_rate < 5, f"Error rate too high under stress: {error_rate:.2f}%"
        assert requests_per_second > 50, f"RPS too low under stress: {requests_per_second:.2f}"
        assert p99_response_time < 2000, f"99th percentile too high: {p99_response_time:.2f}ms"