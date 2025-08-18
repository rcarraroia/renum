"""
Platform-specific webhook processors
"""

from .base_processor import BaseWebhookProcessor
from .whatsapp_processor import WhatsAppWebhookProcessor
from .telegram_processor import TelegramWebhookProcessor
from .zapier_processor import ZapierWebhookProcessor
from .n8n_processor import N8nWebhookProcessor
from .make_processor import MakeWebhookProcessor

__all__ = [
    'BaseWebhookProcessor',
    'WhatsAppWebhookProcessor',
    'TelegramWebhookProcessor',
    'ZapierWebhookProcessor',
    'N8nWebhookProcessor',
    'MakeWebhookProcessor'
]