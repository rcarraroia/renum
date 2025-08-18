"""
Configurações do Sistema de Sandbox
Configurações centralizadas para execução isolada de agentes
"""
from typing import Dict, List, Any
from pydantic import BaseSettings, Field
import os

class SandboxSettings(BaseSettings):
    """Configurações do sistema de sandbox"""
    
    # Docker Configuration
    SANDBOX_DOCKER_HOST: str = Field(
        default="unix://var/run/docker.sock",
        description="Docker host socket"
    )
    
    SANDBOX_BASE_IMAGE: str = Field(
        default="python:3.11-slim",
        description="Imagem base para containers sandbox"
    )
    
    SANDBOX_NETWORK_NAME: str = Field(
        default="renum-sandbox",
        description="Nome da rede isolada para sandboxes"
    )
    
    # Resource Limits
    SANDBOX_MAX_CONCURRENT: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Máximo de sandboxes concorrentes"
    )
    
    SANDBOX_DEFAULT_CPU_CORES: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="CPU cores padrão por sandbox"
    )
    
    SANDBOX_DEFAULT_MEMORY_MB: int = Field(
        default=512,
        ge=128,
        le=2048,
        description="Memória padrão por sandbox (MB)"
    )
    
    SANDBOX_DEFAULT_DISK_MB: int = Field(
        default=1024,
        ge=256,
        le=4096,
        description="Espaço em disco padrão por sandbox (MB)"
    )
    
    SANDBOX_DEFAULT_TIMEOUT_SECONDS: int = Field(
        default=300,
        ge=10,
        le=1800,
        description="Timeout padrão de execução (segundos)"
    )
    
    # Security Settings
    SANDBOX_NETWORK_ISOLATION: bool = Field(
        default=True,
        description="Isolar rede dos sandboxes"
    )
    
    SANDBOX_ALLOWED_DOMAINS: List[str] = Field(
        default_factory=lambda: [
            "api.whatsapp.com",
            "api.telegram.org", 
            "smtp.gmail.com",
            "httpbin.org"  # Para testes
        ],
        description="Domínios permitidos para acesso externo"
    )
    
    SANDBOX_BLOCKED_DOMAINS: List[str] = Field(
        default_factory=lambda: [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "169.254.169.254",  # AWS metadata
            "metadata.google.internal"  # GCP metadata
        ],
        description="Domínios bloqueados para segurança"
    )
    
    SANDBOX_ENABLE_INTERNET_ACCESS: bool = Field(
        default=False,
        description="Permitir acesso à internet (apenas domínios permitidos)"
    )
    
    # Cleanup Settings
    SANDBOX_AUTO_CLEANUP_ENABLED: bool = Field(
        default=True,
        description="Limpeza automática de sandboxes"
    )
    
    SANDBOX_CLEANUP_INTERVAL_MINUTES: int = Field(
        default=15,
        ge=5,
        le=60,
        description="Intervalo de limpeza automática (minutos)"
    )
    
    SANDBOX_MAX_AGE_HOURS: int = Field(
        default=1,
        ge=1,
        le=24,
        description="Idade máxima de sandbox antes da limpeza (horas)"
    )
    
    # Logging and Monitoring
    SANDBOX_LOG_LEVEL: str = Field(
        default="INFO",
        description="Nível de log para sandboxes"
    )
    
    SANDBOX_COLLECT_METRICS: bool = Field(
        default=True,
        description="Coletar métricas de execução"
    )
    
    SANDBOX_METRICS_RETENTION_DAYS: int = Field(
        default=30,
        ge=7,
        le=90,
        description="Retenção de métricas (dias)"
    )
    
    # Mock Integration Settings
    SANDBOX_MOCK_INTEGRATIONS_ENABLED: bool = Field(
        default=True,
        description="Habilitar integrações mock"
    )
    
    SANDBOX_MOCK_RESPONSE_DELAY_MS: int = Field(
        default=100,
        ge=0,
        le=5000,
        description="Delay padrão para respostas mock (ms)"
    )
    
    # Storage Settings
    SANDBOX_TEMP_DIR: str = Field(
        default="/tmp/renum-sandboxes",
        description="Diretório temporário para sandboxes"
    )
    
    SANDBOX_LOGS_DIR: str = Field(
        default="/var/log/renum/sandboxes",
        description="Diretório para logs de sandbox"
    )
    
    # Development Settings
    SANDBOX_DEBUG_MODE: bool = Field(
        default=False,
        description="Modo debug (manter containers após execução)"
    )
    
    SANDBOX_ALLOW_PRIVILEGED: bool = Field(
        default=False,
        description="Permitir containers privilegiados (PERIGOSO)"
    )
    
    class Config:
        env_prefix = "SANDBOX_"
        case_sensitive = True

# Configurações de mock por tipo de integração
MOCK_INTEGRATION_CONFIGS: Dict[str, Dict[str, Any]] = {
    "whatsapp": {
        "base_url": "https://graph.facebook.com/v18.0",
        "default_response": {
            "messages": [{"id": "wamid_mock_123456"}],
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+5511999999999", "wa_id": "5511999999999"}]
        },
        "endpoints": [
            {
                "endpoint": "/messages",
                "method": "POST",
                "response": {
                    "messages": [{"id": "wamid_mock_{{timestamp}}"}],
                    "messaging_product": "whatsapp"
                },
                "status_code": 200,
                "delay_ms": 150
            },
            {
                "endpoint": "/media",
                "method": "POST",
                "response": {
                    "id": "media_mock_{{timestamp}}"
                },
                "status_code": 200,
                "delay_ms": 200
            }
        ]
    },
    
    "telegram": {
        "base_url": "https://api.telegram.org/bot",
        "default_response": {
            "ok": True,
            "result": {
                "message_id": 123,
                "date": 1640995200,
                "text": "Mock response"
            }
        },
        "endpoints": [
            {
                "endpoint": "/sendMessage",
                "method": "POST",
                "response": {
                    "ok": True,
                    "result": {
                        "message_id": "{{random_int}}",
                        "from": {
                            "id": 123456789,
                            "is_bot": True,
                            "first_name": "Test Bot"
                        },
                        "chat": {
                            "id": "{{chat_id}}",
                            "type": "private"
                        },
                        "date": "{{timestamp}}",
                        "text": "{{message}}"
                    }
                },
                "status_code": 200,
                "delay_ms": 100
            },
            {
                "endpoint": "/sendPhoto",
                "method": "POST",
                "response": {
                    "ok": True,
                    "result": {
                        "message_id": "{{random_int}}",
                        "photo": [
                            {
                                "file_id": "photo_mock_{{timestamp}}",
                                "file_unique_id": "unique_{{timestamp}}",
                                "width": 1280,
                                "height": 720,
                                "file_size": 65536
                            }
                        ]
                    }
                },
                "status_code": 200,
                "delay_ms": 300
            }
        ]
    },
    
    "gmail": {
        "base_url": "https://gmail.googleapis.com/gmail/v1",
        "default_response": {
            "id": "mock_message_id",
            "threadId": "mock_thread_id",
            "labelIds": ["SENT"]
        },
        "endpoints": [
            {
                "endpoint": "/users/me/messages/send",
                "method": "POST",
                "response": {
                    "id": "gmail_mock_{{timestamp}}",
                    "threadId": "thread_mock_{{timestamp}}",
                    "labelIds": ["SENT"]
                },
                "status_code": 200,
                "delay_ms": 250
            },
            {
                "endpoint": "/users/me/messages",
                "method": "GET",
                "response": {
                    "messages": [
                        {
                            "id": "msg_mock_1",
                            "threadId": "thread_mock_1"
                        }
                    ],
                    "nextPageToken": "next_page_token",
                    "resultSizeEstimate": 1
                },
                "status_code": 200,
                "delay_ms": 100
            }
        ]
    },
    
    "http_generic": {
        "base_url": "https://httpbin.org",
        "default_response": {
            "status": "ok",
            "mock": True,
            "timestamp": "{{timestamp}}"
        },
        "endpoints": [
            {
                "endpoint": "/get",
                "method": "GET",
                "response": {
                    "args": {},
                    "headers": {
                        "Host": "httpbin.org",
                        "User-Agent": "Renum-Sandbox/1.0"
                    },
                    "origin": "127.0.0.1",
                    "url": "https://httpbin.org/get"
                },
                "status_code": 200,
                "delay_ms": 50
            },
            {
                "endpoint": "/post",
                "method": "POST",
                "response": {
                    "args": {},
                    "data": "{{request_body}}",
                    "files": {},
                    "form": {},
                    "headers": {
                        "Content-Type": "application/json",
                        "Host": "httpbin.org"
                    },
                    "json": "{{request_json}}",
                    "origin": "127.0.0.1",
                    "url": "https://httpbin.org/post"
                },
                "status_code": 200,
                "delay_ms": 75
            }
        ]
    }
}

# Templates de teste pré-definidos
SANDBOX_TEST_TEMPLATES: List[Dict[str, Any]] = [
    {
        "template_id": "whatsapp-send-message",
        "name": "WhatsApp - Send Message",
        "description": "Teste básico de envio de mensagem via WhatsApp",
        "agent_id": "sa-whatsapp",
        "capability": "send_message",
        "default_input": {
            "phone_number": "+5511999999999",
            "message": "Hello from Renum Sandbox! 🚀"
        },
        "mock_configurations": {
            "whatsapp": MOCK_INTEGRATION_CONFIGS["whatsapp"]
        },
        "expected_output": {
            "success": True,
            "message_id": "wamid_mock_*"
        },
        "resource_quota": {
            "cpu_cores": 0.25,
            "memory_mb": 256,
            "disk_mb": 512,
            "max_execution_time_seconds": 60
        },
        "tags": ["whatsapp", "messaging", "basic"]
    },
    
    {
        "template_id": "telegram-send-message",
        "name": "Telegram - Send Message",
        "description": "Teste básico de envio de mensagem via Telegram",
        "agent_id": "sa-telegram",
        "capability": "send_message",
        "default_input": {
            "chat_id": "123456789",
            "message": "Hello from Renum Sandbox! 🤖"
        },
        "mock_configurations": {
            "telegram": MOCK_INTEGRATION_CONFIGS["telegram"]
        },
        "expected_output": {
            "success": True,
            "message_id": "*"
        },
        "resource_quota": {
            "cpu_cores": 0.25,
            "memory_mb": 256,
            "disk_mb": 512,
            "max_execution_time_seconds": 60
        },
        "tags": ["telegram", "messaging", "basic"]
    },
    
    {
        "template_id": "gmail-send-email",
        "name": "Gmail - Send Email",
        "description": "Teste básico de envio de email via Gmail",
        "agent_id": "sa-gmail",
        "capability": "send_email",
        "default_input": {
            "to": "test@example.com",
            "subject": "Test Email from Renum Sandbox",
            "body": "This is a test email sent from Renum Sandbox environment."
        },
        "mock_configurations": {
            "gmail": MOCK_INTEGRATION_CONFIGS["gmail"]
        },
        "expected_output": {
            "success": True,
            "message_id": "gmail_mock_*"
        },
        "resource_quota": {
            "cpu_cores": 0.25,
            "memory_mb": 256,
            "disk_mb": 512,
            "max_execution_time_seconds": 90
        },
        "tags": ["gmail", "email", "basic"]
    },
    
    {
        "template_id": "http-api-call",
        "name": "HTTP Generic - API Call",
        "description": "Teste de chamada HTTP genérica",
        "agent_id": "sa-http-generic",
        "capability": "api_call",
        "default_input": {
            "url": "https://httpbin.org/get",
            "method": "GET",
            "headers": {
                "User-Agent": "Renum-Sandbox/1.0"
            }
        },
        "mock_configurations": {
            "http_generic": MOCK_INTEGRATION_CONFIGS["http_generic"]
        },
        "expected_output": {
            "success": True,
            "status_code": 200
        },
        "resource_quota": {
            "cpu_cores": 0.25,
            "memory_mb": 256,
            "disk_mb": 512,
            "max_execution_time_seconds": 30
        },
        "tags": ["http", "api", "generic"]
    },
    
    {
        "template_id": "multi-step-workflow",
        "name": "Multi-Step Workflow Test",
        "description": "Teste de workflow com múltiplos passos",
        "agent_id": "sa-orchestrator",
        "capability": "execute_workflow",
        "default_input": {
            "workflow_definition": {
                "name": "Test Multi-Step",
                "steps": [
                    {
                        "id": "step1",
                        "agent_id": "sa-http-generic",
                        "capability": "api_call",
                        "input": {
                            "url": "https://httpbin.org/get",
                            "method": "GET"
                        }
                    },
                    {
                        "id": "step2",
                        "agent_id": "sa-whatsapp",
                        "capability": "send_message",
                        "input": {
                            "phone_number": "+5511999999999",
                            "message": "Workflow completed successfully!"
                        }
                    }
                ]
            }
        },
        "mock_configurations": {
            "http_generic": MOCK_INTEGRATION_CONFIGS["http_generic"],
            "whatsapp": MOCK_INTEGRATION_CONFIGS["whatsapp"]
        },
        "expected_output": {
            "success": True,
            "steps_completed": 2
        },
        "resource_quota": {
            "cpu_cores": 0.5,
            "memory_mb": 512,
            "disk_mb": 1024,
            "max_execution_time_seconds": 120
        },
        "tags": ["workflow", "multi-step", "orchestrator"]
    }
]

# Instância global das configurações
sandbox_settings = SandboxSettings()