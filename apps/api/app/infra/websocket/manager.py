"""
Gerenciador de WebSocket para comunicação em tempo real.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerencia conexões WebSocket."""
    
    def __init__(self):
        # Conexões ativas: {user_id: [websockets]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Subscriptions: {user_id: {execution_id: True}}
        self.subscriptions: Dict[str, Dict[str, bool]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Aceita uma nova conexão WebSocket."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
            self.subscriptions[user_id] = {}
        
        self.active_connections[user_id].append(websocket)
        
        logger.info(f"WebSocket connected for user {user_id}")
        
        # Envia mensagem de boas-vindas
        await self.send_personal_message({
            "type": "connection_established",
            "data": {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "WebSocket connection established"
            }
        }, websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove uma conexão WebSocket."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # Remove user se não há mais conexões
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if user_id in self.subscriptions:
                    del self.subscriptions[user_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Envia mensagem para uma conexão específica."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message to websocket: {e}")
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Envia mensagem para todas as conexões de um usuário."""
        if user_id in self.active_connections:
            disconnected = []
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")
                    disconnected.append(websocket)
            
            # Remove conexões mortas
            for ws in disconnected:
                self.active_connections[user_id].remove(ws)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Envia mensagem para todas as conexões ativas."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(message, user_id)
    
    def subscribe_to_execution(self, user_id: str, execution_id: str):
        """Inscreve usuário para receber atualizações de uma execução."""
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = {}
        
        self.subscriptions[user_id][execution_id] = True
        logger.info(f"User {user_id} subscribed to execution {execution_id}")
    
    def unsubscribe_from_execution(self, user_id: str, execution_id: str):
        """Remove inscrição de atualizações de execução."""
        if user_id in self.subscriptions and execution_id in self.subscriptions[user_id]:
            del self.subscriptions[user_id][execution_id]
            logger.info(f"User {user_id} unsubscribed from execution {execution_id}")
    
    async def notify_execution_update(self, execution_id: str, user_id: str, update_data: Dict[str, Any]):
        """Notifica atualizações de execução para usuários inscritos."""
        # Verifica se o usuário está inscrito nesta execução
        if (user_id in self.subscriptions and 
            execution_id in self.subscriptions[user_id]):
            
            message = {
                "type": "execution_status_update",
                "data": {
                    "execution_id": execution_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **update_data
                }
            }
            
            await self.send_to_user(message, user_id)
    
    async def notify_agent_completed(self, execution_id: str, user_id: str, agent_data: Dict[str, Any]):
        """Notifica conclusão de agente."""
        if (user_id in self.subscriptions and 
            execution_id in self.subscriptions[user_id]):
            
            message = {
                "type": "agent_completed",
                "data": {
                    "execution_id": execution_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **agent_data
                }
            }
            
            await self.send_to_user(message, user_id)
    
    async def notify_team_updated(self, team_id: str, user_id: str, team_data: Dict[str, Any]):
        """Notifica atualizações de equipe."""
        message = {
            "type": "team_updated",
            "data": {
                "team_id": team_id,
                "timestamp": datetime.utcnow().isoformat(),
                **team_data
            }
        }
        
        await self.send_to_user(message, user_id)
    
    async def send_notification(self, user_id: str, notification_data: Dict[str, Any]):
        """Envia notificação geral para usuário."""
        message = {
            "type": "new_notification",
            "data": {
                "timestamp": datetime.utcnow().isoformat(),
                **notification_data
            }
        }
        
        await self.send_to_user(message, user_id)
    
    def get_connection_count(self) -> int:
        """Retorna número total de conexões ativas."""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Retorna número de conexões de um usuário."""
        return len(self.active_connections.get(user_id, []))


# Instância global do gerenciador
manager = ConnectionManager()


def get_websocket_manager() -> ConnectionManager:
    """Dependency injection para o gerenciador de WebSocket."""
    return manager