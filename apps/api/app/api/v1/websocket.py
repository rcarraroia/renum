"""
Endpoint WebSocket para comunicação em tempo real.
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, Any
import logging

from app.infra.websocket.manager import get_websocket_manager, ConnectionManager
from app.core.security import get_current_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    manager: ConnectionManager = Depends(get_websocket_manager)
):
    """
    Endpoint WebSocket para comunicação em tempo real.
    
    Args:
        websocket: Conexão WebSocket
        token: JWT token para autenticação
        manager: Gerenciador de conexões WebSocket
        
    Query Parameters:
        token: JWT token de autenticação
        
    Eventos suportados:
        - connection_established: Conexão estabelecida
        - execution_status_update: Atualização de status de execução
        - agent_completed: Agente completou execução
        - team_updated: Equipe foi atualizada
        - new_notification: Nova notificação
        - subscribe_execution: Inscrever-se em atualizações de execução
        - unsubscribe_execution: Cancelar inscrição de execução
        - ping: Manter conexão viva
    """
    
    # Autentica usuário via token
    try:
        user = await get_current_user_from_token(token)
        user_id = user["id"]
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Conecta usuário
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Recebe mensagens do cliente
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(message, user_id, websocket, manager)
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "data": {
                        "message": "Invalid JSON format"
                    }
                }, websocket)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "data": {
                        "message": "Internal server error"
                    }
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)


async def handle_websocket_message(
    message: Dict[str, Any], 
    user_id: str, 
    websocket: WebSocket, 
    manager: ConnectionManager
):
    """
    Processa mensagens recebidas via WebSocket.
    
    Args:
        message: Mensagem recebida
        user_id: ID do usuário
        websocket: Conexão WebSocket
        manager: Gerenciador de conexões
    """
    
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == "subscribe_execution":
        # Inscreve usuário em atualizações de execução
        execution_id = data.get("execution_id")
        if execution_id:
            manager.subscribe_to_execution(user_id, execution_id)
            await manager.send_personal_message({
                "type": "subscription_confirmed",
                "data": {
                    "execution_id": execution_id,
                    "message": "Subscribed to execution updates"
                }
            }, websocket)
        else:
            await manager.send_personal_message({
                "type": "error",
                "data": {
                    "message": "execution_id is required for subscription"
                }
            }, websocket)
    
    elif message_type == "unsubscribe_execution":
        # Remove inscrição de execução
        execution_id = data.get("execution_id")
        if execution_id:
            manager.unsubscribe_from_execution(user_id, execution_id)
            await manager.send_personal_message({
                "type": "unsubscription_confirmed",
                "data": {
                    "execution_id": execution_id,
                    "message": "Unsubscribed from execution updates"
                }
            }, websocket)
    
    elif message_type == "ping":
        # Responde ao ping para manter conexão viva
        await manager.send_personal_message({
            "type": "pong",
            "data": {
                "message": "Connection alive"
            }
        }, websocket)
    
    elif message_type == "get_status":
        # Retorna status da conexão
        await manager.send_personal_message({
            "type": "status",
            "data": {
                "user_id": user_id,
                "connections": manager.get_user_connection_count(user_id),
                "total_connections": manager.get_connection_count(),
                "subscriptions": list(manager.subscriptions.get(user_id, {}).keys())
            }
        }, websocket)
    
    else:
        # Tipo de mensagem não reconhecido
        await manager.send_personal_message({
            "type": "error",
            "data": {
                "message": f"Unknown message type: {message_type}"
            }
        }, websocket)