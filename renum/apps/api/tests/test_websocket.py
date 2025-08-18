"""
Testes para funcionalidades de WebSocket.
"""

import pytest
import json
import asyncio
from fastapi.testclient import TestClient
from fastapi import WebSocket
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.main import app
from app.infra.websocket.manager import ConnectionManager
from app.api.v1.websocket import handle_websocket_message

client = TestClient(app)


class TestWebSocketManager:
    """Testes para o gerenciador de conexões WebSocket."""
    
    @pytest.fixture
    def manager(self):
        """Instância do gerenciador para testes."""
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Mock de WebSocket para testes."""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_connect_user(self, manager, mock_websocket):
        """Testa conexão de usuário."""
        user_id = "test-user-123"
        
        await manager.connect(mock_websocket, user_id)
        
        # Verifica se websocket foi aceito
        mock_websocket.accept.assert_called_once()
        
        # Verifica se usuário foi adicionado às conexões ativas
        assert user_id in manager.active_connections
        assert mock_websocket in manager.active_connections[user_id]
        assert user_id in manager.subscriptions
        
        # Verifica se mensagem de boas-vindas foi enviada
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "connection_established"
        assert message["data"]["user_id"] == user_id
    
    def test_disconnect_user(self, manager, mock_websocket):
        """Testa desconexão de usuário."""
        user_id = "test-user-123"
        
        # Adiciona conexão manualmente
        manager.active_connections[user_id] = [mock_websocket]
        manager.subscriptions[user_id] = {}
        
        # Desconecta
        manager.disconnect(mock_websocket, user_id)
        
        # Verifica se usuário foi removido
        assert user_id not in manager.active_connections
        assert user_id not in manager.subscriptions
    
    def test_disconnect_user_multiple_connections(self, manager, mock_websocket):
        """Testa desconexão quando usuário tem múltiplas conexões."""
        user_id = "test-user-123"
        other_websocket = Mock(spec=WebSocket)
        
        # Adiciona múltiplas conexões
        manager.active_connections[user_id] = [mock_websocket, other_websocket]
        manager.subscriptions[user_id] = {}
        
        # Desconecta apenas uma
        manager.disconnect(mock_websocket, user_id)
        
        # Verifica se apenas uma conexão foi removida
        assert user_id in manager.active_connections
        assert mock_websocket not in manager.active_connections[user_id]
        assert other_websocket in manager.active_connections[user_id]
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """Testa envio de mensagem pessoal."""
        message = {"type": "test", "data": {"content": "Hello"}}
        
        await manager.send_personal_message(message, mock_websocket)
        
        mock_websocket.send_text.assert_called_once_with(json.dumps(message))
    
    @pytest.mark.asyncio
    async def test_send_personal_message_error(self, manager, mock_websocket):
        """Testa tratamento de erro no envio de mensagem pessoal."""
        mock_websocket.send_text.side_effect = Exception("Connection error")
        message = {"type": "test", "data": {"content": "Hello"}}
        
        # Não deve levantar exceção
        await manager.send_personal_message(message, mock_websocket)
    
    @pytest.mark.asyncio
    async def test_send_to_user(self, manager, mock_websocket):
        """Testa envio de mensagem para usuário."""
        user_id = "test-user-123"
        message = {"type": "test", "data": {"content": "Hello"}}
        
        # Adiciona conexão
        manager.active_connections[user_id] = [mock_websocket]
        
        await manager.send_to_user(message, user_id)
        
        mock_websocket.send_text.assert_called_once_with(json.dumps(message))
    
    @pytest.mark.asyncio
    async def test_send_to_user_no_connections(self, manager):
        """Testa envio para usuário sem conexões."""
        user_id = "test-user-123"
        message = {"type": "test", "data": {"content": "Hello"}}
        
        # Não deve levantar exceção
        await manager.send_to_user(message, user_id)
    
    @pytest.mark.asyncio
    async def test_send_to_user_with_dead_connection(self, manager, mock_websocket):
        """Testa envio para usuário com conexão morta."""
        user_id = "test-user-123"
        message = {"type": "test", "data": {"content": "Hello"}}
        
        # Simula conexão morta
        mock_websocket.send_text.side_effect = Exception("Connection dead")
        manager.active_connections[user_id] = [mock_websocket]
        
        await manager.send_to_user(message, user_id)
        
        # Conexão morta deve ser removida
        assert mock_websocket not in manager.active_connections[user_id]
    
    def test_subscribe_to_execution(self, manager):
        """Testa inscrição em execução."""
        user_id = "test-user-123"
        execution_id = "exec-456"
        
        manager.subscribe_to_execution(user_id, execution_id)
        
        assert user_id in manager.subscriptions
        assert execution_id in manager.subscriptions[user_id]
        assert manager.subscriptions[user_id][execution_id] is True
    
    def test_unsubscribe_from_execution(self, manager):
        """Testa cancelamento de inscrição."""
        user_id = "test-user-123"
        execution_id = "exec-456"
        
        # Adiciona inscrição
        manager.subscriptions[user_id] = {execution_id: True}
        
        manager.unsubscribe_from_execution(user_id, execution_id)
        
        assert execution_id not in manager.subscriptions[user_id]
    
    def test_unsubscribe_nonexistent(self, manager):
        """Testa cancelamento de inscrição inexistente."""
        user_id = "test-user-123"
        execution_id = "exec-456"
        
        # Não deve levantar exceção
        manager.unsubscribe_from_execution(user_id, execution_id)
    
    @pytest.mark.asyncio
    async def test_notify_execution_update(self, manager, mock_websocket):
        """Testa notificação de atualização de execução."""
        user_id = "test-user-123"
        execution_id = "exec-456"
        update_data = {"status": "running", "progress": 50}
        
        # Configura usuário inscrito
        manager.active_connections[user_id] = [mock_websocket]
        manager.subscriptions[user_id] = {execution_id: True}
        
        await manager.notify_execution_update(execution_id, user_id, update_data)
        
        # Verifica se mensagem foi enviada
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        
        assert message["type"] == "execution_status_update"
        assert message["data"]["execution_id"] == execution_id
        assert message["data"]["status"] == "running"
        assert message["data"]["progress"] == 50
    
    @pytest.mark.asyncio
    async def test_notify_execution_update_not_subscribed(self, manager, mock_websocket):
        """Testa notificação para usuário não inscrito."""
        user_id = "test-user-123"
        execution_id = "exec-456"
        update_data = {"status": "running"}
        
        # Usuário não inscrito
        manager.active_connections[user_id] = [mock_websocket]
        manager.subscriptions[user_id] = {}
        
        await manager.notify_execution_update(execution_id, user_id, update_data)
        
        # Não deve enviar mensagem
        mock_websocket.send_text.assert_not_called()
    
    def test_get_connection_count(self, manager, mock_websocket):
        """Testa contagem de conexões."""
        user1 = "user-1"
        user2 = "user-2"
        
        manager.active_connections[user1] = [mock_websocket]
        manager.active_connections[user2] = [mock_websocket, mock_websocket]
        
        assert manager.get_connection_count() == 3
    
    def test_get_user_connection_count(self, manager, mock_websocket):
        """Testa contagem de conexões por usuário."""
        user_id = "test-user-123"
        
        manager.active_connections[user_id] = [mock_websocket, mock_websocket]
        
        assert manager.get_user_connection_count(user_id) == 2
        assert manager.get_user_connection_count("nonexistent") == 0


class TestWebSocketMessageHandling:
    """Testes para tratamento de mensagens WebSocket."""
    
    @pytest.fixture
    def manager(self):
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_handle_subscribe_execution(self, manager, mock_websocket):
        """Testa inscrição em execução via mensagem."""
        user_id = "test-user-123"
        execution_id = "exec-456"
        message = {
            "type": "subscribe_execution",
            "data": {"execution_id": execution_id}
        }
        
        await handle_websocket_message(message, user_id, mock_websocket, manager)
        
        # Verifica inscrição
        assert execution_id in manager.subscriptions.get(user_id, {})
        
        # Verifica resposta de confirmação
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        assert response["type"] == "subscription_confirmed"
        assert response["data"]["execution_id"] == execution_id
    
    @pytest.mark.asyncio
    async def test_handle_subscribe_execution_missing_id(self, manager, mock_websocket):
        """Testa inscrição sem execution_id."""
        user_id = "test-user-123"
        message = {
            "type": "subscribe_execution",
            "data": {}
        }
        
        await handle_websocket_message(message, user_id, mock_websocket, manager)
        
        # Verifica resposta de erro
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        assert response["type"] == "error"
        assert "execution_id is required" in response["data"]["message"]
    
    @pytest.mark.asyncio
    async def test_handle_unsubscribe_execution(self, manager, mock_websocket):
        """Testa cancelamento de inscrição via mensagem."""
        user_id = "test-user-123"
        execution_id = "exec-456"
        
        # Adiciona inscrição primeiro
        manager.subscriptions[user_id] = {execution_id: True}
        
        message = {
            "type": "unsubscribe_execution",
            "data": {"execution_id": execution_id}
        }
        
        await handle_websocket_message(message, user_id, mock_websocket, manager)
        
        # Verifica remoção da inscrição
        assert execution_id not in manager.subscriptions.get(user_id, {})
        
        # Verifica resposta de confirmação
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        assert response["type"] == "unsubscription_confirmed"
    
    @pytest.mark.asyncio
    async def test_handle_ping(self, manager, mock_websocket):
        """Testa ping/pong."""
        user_id = "test-user-123"
        message = {"type": "ping", "data": {}}
        
        await handle_websocket_message(message, user_id, mock_websocket, manager)
        
        # Verifica resposta pong
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        assert response["type"] == "pong"
    
    @pytest.mark.asyncio
    async def test_handle_get_status(self, manager, mock_websocket):
        """Testa obtenção de status."""
        user_id = "test-user-123"
        execution_id = "exec-456"
        
        # Configura estado
        manager.active_connections[user_id] = [mock_websocket]
        manager.subscriptions[user_id] = {execution_id: True}
        
        message = {"type": "get_status", "data": {}}
        
        await handle_websocket_message(message, user_id, mock_websocket, manager)
        
        # Verifica resposta de status
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        
        assert response["type"] == "status"
        assert response["data"]["user_id"] == user_id
        assert response["data"]["connections"] == 1
        assert execution_id in response["data"]["subscriptions"]
    
    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, manager, mock_websocket):
        """Testa mensagem com tipo desconhecido."""
        user_id = "test-user-123"
        message = {"type": "unknown_type", "data": {}}
        
        await handle_websocket_message(message, user_id, mock_websocket, manager)
        
        # Verifica resposta de erro
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        assert response["type"] == "error"
        assert "Unknown message type" in response["data"]["message"]


class TestWebSocketIntegration:
    """Testes de integração para WebSocket."""
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_flow(self):
        """Testa fluxo de autenticação WebSocket."""
        # Este teste seria mais completo com mock da autenticação
        pass
    
    @pytest.mark.asyncio
    async def test_websocket_execution_notifications(self):
        """Testa notificações de execução via WebSocket."""
        # Este teste seria mais completo com integração real
        pass
    
    @pytest.mark.asyncio
    async def test_websocket_multiple_clients(self):
        """Testa múltiplos clientes conectados."""
        # Este teste seria mais completo com TestClient WebSocket
        pass