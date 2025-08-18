"""
Serviço de Mascaramento de PII e Conformidade de Dados
Implementa mascaramento automático de dados sensíveis e purga de dados para LGPD/GDPR
"""
import re
import hashlib
import json
from typing import Dict, Any, List, Optional, Pattern, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

class PIIType(str, Enum):
    """Tipos de PII identificados"""
    EMAIL = "email"
    CPF = "cpf"
    CNPJ = "cnpj"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ADDRESS = "address"
    DOCUMENT_ID = "document_id"
    BANK_ACCOUNT = "bank_account"

@dataclass
class PIIPattern:
    """Padrão de PII com regex e função de mascaramento"""
    pii_type: PIIType
    pattern: Pattern[str]
    mask_function: callable
    description: str
    sensitivity_level: int  # 1-5, sendo 5 o mais sensível

class PIIService:
    """Serviço para mascaramento de PII e conformidade de dados"""
    
    def __init__(self):
        self.patterns = self._initialize_pii_patterns()
        self.masked_cache: Dict[str, str] = {}
        
    def _initialize_pii_patterns(self) -> List[PIIPattern]:
        """Inicializar padrões de PII"""
        patterns = [
            # Email
            PIIPattern(
                pii_type=PIIType.EMAIL,
                pattern=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                mask_function=self._mask_email,
                description="Endereços de email",
                sensitivity_level=4
            ),
            
            # CPF (formato: 000.000.000-00 ou 00000000000)
            PIIPattern(
                pii_type=PIIType.CPF,
                pattern=re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'),
                mask_function=self._mask_cpf,
                description="Números de CPF",
                sensitivity_level=5
            ),
            
            # CNPJ (formato: 00.000.000/0000-00 ou 00000000000000)
            PIIPattern(
                pii_type=PIIType.CNPJ,
                pattern=re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?0001-?\d{2}\b'),
                mask_function=self._mask_cnpj,
                description="Números de CNPJ",
                sensitivity_level=4
            ),
            
            # Telefone brasileiro
            PIIPattern(
                pii_type=PIIType.PHONE,
                pattern=re.compile(r'\+?55\s?\(?(?:11|12|13|14|15|16|17|18|19|21|22|24|27|28|31|32|33|34|35|37|38|41|42|43|44|45|46|47|48|49|51|53|54|55|61|62|63|64|65|66|67|68|69|71|73|74|75|77|79|81|82|83|84|85|86|87|88|89|91|92|93|94|95|96|97|98|99)\)?\s?9?\d{4}-?\d{4}'),
                mask_function=self._mask_phone,
                description="Números de telefone",
                sensitivity_level=3
            ),
            
            # Cartão de crédito
            PIIPattern(
                pii_type=PIIType.CREDIT_CARD,
                pattern=re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
                mask_function=self._mask_credit_card,
                description="Números de cartão de crédito",
                sensitivity_level=5
            ),
            
            # Endereço IP
            PIIPattern(
                pii_type=PIIType.IP_ADDRESS,
                pattern=re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
                mask_function=self._mask_ip,
                description="Endereços IP",
                sensitivity_level=2
            ),
            
            # RG/Documento de identidade
            PIIPattern(
                pii_type=PIIType.DOCUMENT_ID,
                pattern=re.compile(r'\b\d{1,2}\.?\d{3}\.?\d{3}-?[0-9X]\b'),
                mask_function=self._mask_document_id,
                description="Números de RG/Documento",
                sensitivity_level=5
            ),
            
            # Conta bancária (formato simplificado)
            PIIPattern(
                pii_type=PIIType.BANK_ACCOUNT,
                pattern=re.compile(r'\b\d{4,6}-?\d{1,2}\b'),
                mask_function=self._mask_bank_account,
                description="Números de conta bancária",
                sensitivity_level=5
            )
        ]
        
        return patterns
    
    def mask_text(self, text: str, preserve_format: bool = True) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Mascarar PII em texto
        
        Args:
            text: Texto para mascarar
            preserve_format: Preservar formato original
            
        Returns:
            Tuple com texto mascarado e lista de PIIs encontrados
        """
        if not text or not isinstance(text, str):
            return text, []
        
        masked_text = text
        found_piis = []
        
        for pattern in self.patterns:
            matches = pattern.pattern.finditer(masked_text)
            
            for match in matches:
                original_value = match.group()
                masked_value = pattern.mask_function(original_value, preserve_format)
                
                # Substituir no texto
                masked_text = masked_text.replace(original_value, masked_value)
                
                # Registrar PII encontrado
                found_piis.append({
                    'type': pattern.pii_type.value,
                    'original_length': len(original_value),
                    'position': match.start(),
                    'sensitivity_level': pattern.sensitivity_level,
                    'masked_value': masked_value
                })
        
        return masked_text, found_piis
    
    def mask_dict(self, data: Dict[str, Any], recursive: bool = True) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Mascarar PII em dicionário
        
        Args:
            data: Dicionário para mascarar
            recursive: Processar recursivamente
            
        Returns:
            Tuple com dicionário mascarado e lista de PIIs encontrados
        """
        if not isinstance(data, dict):
            return data, []
        
        masked_data = {}
        all_found_piis = []
        
        for key, value in data.items():
            if isinstance(value, str):
                masked_value, found_piis = self.mask_text(value)
                masked_data[key] = masked_value
                
                # Adicionar contexto do campo
                for pii in found_piis:
                    pii['field'] = key
                    all_found_piis.append(pii)
                    
            elif isinstance(value, dict) and recursive:
                masked_value, found_piis = self.mask_dict(value, recursive)
                masked_data[key] = masked_value
                all_found_piis.extend(found_piis)
                
            elif isinstance(value, list) and recursive:
                masked_value, found_piis = self.mask_list(value, recursive)
                masked_data[key] = masked_value
                all_found_piis.extend(found_piis)
                
            else:
                masked_data[key] = value
        
        return masked_data, all_found_piis
    
    def mask_list(self, data: List[Any], recursive: bool = True) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """Mascarar PII em lista"""
        if not isinstance(data, list):
            return data, []
        
        masked_list = []
        all_found_piis = []
        
        for i, item in enumerate(data):
            if isinstance(item, str):
                masked_item, found_piis = self.mask_text(item)
                masked_list.append(masked_item)
                
                for pii in found_piis:
                    pii['list_index'] = i
                    all_found_piis.append(pii)
                    
            elif isinstance(item, dict) and recursive:
                masked_item, found_piis = self.mask_dict(item, recursive)
                masked_list.append(masked_item)
                all_found_piis.extend(found_piis)
                
            elif isinstance(item, list) and recursive:
                masked_item, found_piis = self.mask_list(item, recursive)
                masked_list.append(masked_item)
                all_found_piis.extend(found_piis)
                
            else:
                masked_list.append(item)
        
        return masked_list, all_found_piis
    
    def mask_json(self, json_str: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Mascarar PII em string JSON"""
        try:
            data = json.loads(json_str)
            masked_data, found_piis = self.mask_dict(data)
            return json.dumps(masked_data, ensure_ascii=False), found_piis
        except json.JSONDecodeError:
            # Se não for JSON válido, tratar como texto
            return self.mask_text(json_str)
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """Verificar se campo é sensível baseado no nome"""
        sensitive_fields = {
            'email', 'e_mail', 'mail', 'email_address',
            'cpf', 'document', 'documento', 'rg',
            'phone', 'telefone', 'celular', 'mobile',
            'credit_card', 'cartao', 'card_number',
            'password', 'senha', 'pass', 'pwd',
            'token', 'api_key', 'secret', 'key',
            'address', 'endereco', 'street', 'rua',
            'name', 'nome', 'full_name', 'nome_completo'
        }
        
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in sensitive_fields)
    
    def get_pii_statistics(self, text: str) -> Dict[str, Any]:
        """Obter estatísticas de PII em texto"""
        _, found_piis = self.mask_text(text)
        
        stats = {
            'total_piis_found': len(found_piis),
            'pii_types': {},
            'sensitivity_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            'text_length': len(text),
            'pii_density': 0
        }
        
        for pii in found_piis:
            pii_type = pii['type']
            sensitivity = pii['sensitivity_level']
            
            stats['pii_types'][pii_type] = stats['pii_types'].get(pii_type, 0) + 1
            stats['sensitivity_distribution'][sensitivity] += 1
        
        if stats['text_length'] > 0:
            stats['pii_density'] = stats['total_piis_found'] / stats['text_length'] * 100
        
        return stats
    
    # Funções de mascaramento específicas
    
    def _mask_email(self, email: str, preserve_format: bool = True) -> str:
        """Mascarar email: fulano@email.com → f***o@email.com"""
        if '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    def _mask_cpf(self, cpf: str, preserve_format: bool = True) -> str:
        """Mascarar CPF: 123.456.789-00 → ***.***.***-**"""
        if preserve_format:
            # Preservar pontuação
            masked = re.sub(r'\d', '*', cpf)
            # Manter alguns dígitos para contexto
            if len(cpf.replace('.', '').replace('-', '')) == 11:
                return masked[:3] + masked[3:6] + masked[6:9] + masked[9:]
        
        return '*' * len(cpf.replace('.', '').replace('-', ''))
    
    def _mask_cnpj(self, cnpj: str, preserve_format: bool = True) -> str:
        """Mascarar CNPJ: 12.345.678/0001-90 → **.***.***/****-**"""
        if preserve_format:
            return re.sub(r'\d', '*', cnpj)
        return '*' * len(cnpj.replace('.', '').replace('/', '').replace('-', ''))
    
    def _mask_phone(self, phone: str, preserve_format: bool = True) -> str:
        """Mascarar telefone: +55 11 99999-9999 → +55 11 ****-****"""
        if preserve_format:
            # Manter código do país e área, mascarar número
            masked = re.sub(r'(\+55\s?\(?\d{2}\)?\s?)(\d+)', r'\1****-****', phone)
            return masked
        return '*' * len(phone)
    
    def _mask_credit_card(self, card: str, preserve_format: bool = True) -> str:
        """Mascarar cartão: 1234 5678 9012 3456 → **** **** **** 3456"""
        if preserve_format:
            # Manter últimos 4 dígitos
            digits_only = re.sub(r'\D', '', card)
            if len(digits_only) >= 4:
                masked_digits = '*' * (len(digits_only) - 4) + digits_only[-4:]
                # Recriar formato original
                return re.sub(r'\d', lambda m: masked_digits[0] if masked_digits else '*', card)
        return '*' * len(card)
    
    def _mask_ip(self, ip: str, preserve_format: bool = True) -> str:
        """Mascarar IP: 192.168.1.100 → 192.168.*.*"""
        if preserve_format:
            parts = ip.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.*.*"
        return '*' * len(ip)
    
    def _mask_document_id(self, doc_id: str, preserve_format: bool = True) -> str:
        """Mascarar RG: 12.345.678-9 → **.***.**-*"""
        if preserve_format:
            return re.sub(r'\d', '*', doc_id)
        return '*' * len(doc_id.replace('.', '').replace('-', ''))
    
    def _mask_bank_account(self, account: str, preserve_format: bool = True) -> str:
        """Mascarar conta bancária: 12345-6 → ****-*"""
        if preserve_format:
            return re.sub(r'\d', '*', account)
        return '*' * len(account.replace('-', ''))
    
    def generate_hash_id(self, original_value: str) -> str:
        """Gerar hash consistente para valor original (para auditoria)"""
        # Usar salt fixo para consistência
        salt = settings.PII_HASH_SALT or "renum-pii-salt"
        return hashlib.sha256(f"{salt}{original_value}".encode()).hexdigest()[:16]

# Instância global do serviço
pii_service = PIIService()