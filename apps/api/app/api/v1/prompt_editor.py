"""
Prompt Editor API endpoints
API backend para criação, edição e gerenciamento de prompts de agentes
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import JSONResponse
import json

from app.schemas.prompt_editor import (
    PromptTemplateSchema,
    CreatePromptTemplateSchema,
    UpdatePromptTemplateSchema,
    PromptRenderRequestSchema,
    PromptRenderResponseSchema,
    PromptTestRequestSchema,
    PromptTestResultSchema,
    PromptVersionSchema,
    PromptAnalyticsSchema,
    PromptValidationSchema,
    PromptCloneRequestSchema,
    PromptExportSchema,
    PromptImportRequestSchema,
    PromptLibrarySchema,
    PromptCategoryEnum,
    PromptStatusEnum
)
from app.services.prompt_editor_service import prompt_editor_service
from app.middleware.admin_auth import require_permission, get_current_admin_user
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/prompt-editor", tags=["Prompt Editor"])

# Template Management Endpoints
@router.post("/templates", response_model=PromptTemplateSchema)
async def create_template(
    template_data: CreatePromptTemplateSchema,
    current_admin = Depends(require_permission("agents:write"))
):
    """Criar novo template de prompt"""
    try:
        template = await prompt_editor_service.create_template(
            name=template_data.name,
            description=template_data.description,
            category=template_data.category,
            type=template_data.type,
            content=template_data.content,
            variables=[var.dict() for var in template_data.variables],
            tags=template_data.tags,
            created_by=current_admin['user_id'],
            metadata=template_data.metadata
        )
        
        return PromptTemplateSchema(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            category=template.category,
            type=template.type,
            content=template.content,
            variables=[
                {
                    "name": var.name,
                    "type": var.type,
                    "description": var.description,
                    "required": var.required,
                    "default_value": var.default_value,
                    "validation_pattern": var.validation_pattern,
                    "min_length": var.min_length,
                    "max_length": var.max_length,
                    "options": var.options
                }
                for var in template.variables
            ],
            tags=template.tags,
            version=template.version,
            status=template.status,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=template.usage_count,
            rating=template.rating,
            metadata=template.metadata
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to create template", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar template: {str(e)}"
        )

@router.get("/templates", response_model=PromptLibrarySchema)
async def list_templates(
    category: Optional[PromptCategoryEnum] = Query(None, description="Filtrar por categoria"),
    status: Optional[PromptStatusEnum] = Query(None, description="Filtrar por status"),
    tags: Optional[str] = Query(None, description="Filtrar por tags (separadas por vírgula)"),
    search: Optional[str] = Query(None, description="Buscar por nome ou descrição"),
    limit: int = Query(50, ge=1, le=100, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    current_admin = Depends(require_permission("agents:read"))
):
    """Listar templates de prompt com filtros"""
    try:
        # Converter tags de string para lista
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
        
        templates = await prompt_editor_service.list_templates(
            category=category,
            status=status,
            tags=tag_list,
            search=search,
            limit=limit,
            offset=offset
        )
        
        # Converter para schema
        template_schemas = []
        for template in templates:
            template_schemas.append(PromptTemplateSchema(
                template_id=template.template_id,
                name=template.name,
                description=template.description,
                category=template.category,
                type=template.type,
                content=template.content,
                variables=[
                    {
                        "name": var.name,
                        "type": var.type,
                        "description": var.description,
                        "required": var.required,
                        "default_value": var.default_value,
                        "validation_pattern": var.validation_pattern,
                        "min_length": var.min_length,
                        "max_length": var.max_length,
                        "options": var.options
                    }
                    for var in template.variables
                ],
                tags=template.tags,
                version=template.version,
                status=template.status,
                created_by=template.created_by,
                created_at=template.created_at,
                updated_at=template.updated_at,
                usage_count=template.usage_count,
                rating=template.rating,
                metadata=template.metadata
            ))
        
        # Obter estatísticas da biblioteca
        all_templates = await prompt_editor_service.list_templates(limit=1000)
        categories = list(set(t.category.value for t in all_templates))
        all_tags = []
        for t in all_templates:
            all_tags.extend(t.tags)
        unique_tags = list(set(all_tags))
        
        return PromptLibrarySchema(
            templates=template_schemas,
            total_count=len(all_templates),
            categories=categories,
            tags=unique_tags
        )
        
    except Exception as e:
        logger.error("Failed to list templates", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar templates: {str(e)}"
        )

@router.get("/templates/{template_id}", response_model=PromptTemplateSchema)
async def get_template(
    template_id: str,
    current_admin = Depends(require_permission("agents:read"))
):
    """Obter template específico"""
    try:
        template = await prompt_editor_service.get_template(template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' não encontrado"
            )
        
        return PromptTemplateSchema(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            category=template.category,
            type=template.type,
            content=template.content,
            variables=[
                {
                    "name": var.name,
                    "type": var.type,
                    "description": var.description,
                    "required": var.required,
                    "default_value": var.default_value,
                    "validation_pattern": var.validation_pattern,
                    "min_length": var.min_length,
                    "max_length": var.max_length,
                    "options": var.options
                }
                for var in template.variables
            ],
            tags=template.tags,
            version=template.version,
            status=template.status,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=template.usage_count,
            rating=template.rating,
            metadata=template.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get template", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter template: {str(e)}"
        )

@router.put("/templates/{template_id}", response_model=PromptTemplateSchema)
async def update_template(
    template_id: str,
    updates: UpdatePromptTemplateSchema,
    changelog: str = Query("", description="Descrição das mudanças"),
    current_admin = Depends(require_permission("agents:write"))
):
    """Atualizar template existente"""
    try:
        # Converter updates para dict, removendo valores None
        update_dict = {}
        if updates.name is not None:
            update_dict['name'] = updates.name
        if updates.description is not None:
            update_dict['description'] = updates.description
        if updates.category is not None:
            update_dict['category'] = updates.category
        if updates.content is not None:
            update_dict['content'] = updates.content
        if updates.variables is not None:
            update_dict['variables'] = [var.dict() for var in updates.variables]
        if updates.tags is not None:
            update_dict['tags'] = updates.tags
        if updates.status is not None:
            update_dict['status'] = updates.status
        if updates.metadata is not None:
            update_dict['metadata'] = updates.metadata
        
        template = await prompt_editor_service.update_template(
            template_id=template_id,
            updates=update_dict,
            updated_by=current_admin['user_id'],
            changelog=changelog
        )
        
        return PromptTemplateSchema(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            category=template.category,
            type=template.type,
            content=template.content,
            variables=[
                {
                    "name": var.name,
                    "type": var.type,
                    "description": var.description,
                    "required": var.required,
                    "default_value": var.default_value,
                    "validation_pattern": var.validation_pattern,
                    "min_length": var.min_length,
                    "max_length": var.max_length,
                    "options": var.options
                }
                for var in template.variables
            ],
            tags=template.tags,
            version=template.version,
            status=template.status,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=template.usage_count,
            rating=template.rating,
            metadata=template.metadata
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to update template", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar template: {str(e)}"
        )

@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_admin = Depends(require_permission("agents:write"))
):
    """Deletar template"""
    try:
        success = await prompt_editor_service.delete_template(
            template_id=template_id,
            deleted_by=current_admin['user_id']
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' não encontrado"
            )
        
        return {"message": f"Template '{template_id}' deletado com sucesso"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete template", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar template: {str(e)}"
        )

# Prompt Rendering and Testing Endpoints
@router.post("/templates/{template_id}/render", response_model=PromptRenderResponseSchema)
async def render_prompt(
    template_id: str,
    render_request: PromptRenderRequestSchema,
    current_admin = Depends(require_permission("agents:read"))
):
    """Renderizar prompt com variáveis"""
    try:
        rendered_content, metadata = await prompt_editor_service.render_prompt(
            template_id=template_id,
            variables=render_request.variables,
            version=render_request.version
        )
        
        return PromptRenderResponseSchema(
            rendered_content=rendered_content,
            metadata=metadata
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to render prompt", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao renderizar prompt: {str(e)}"
        )

@router.post("/templates/{template_id}/test", response_model=PromptTestResultSchema)
async def test_prompt_in_sandbox(
    template_id: str,
    test_request: PromptTestRequestSchema,
    current_admin = Depends(require_permission("agents:write"))
):
    """Testar prompt no ambiente sandbox"""
    try:
        test_result = await prompt_editor_service.test_prompt_in_sandbox(
            template_id=template_id,
            variables=test_request.variables,
            test_input=test_request.test_input,
            tested_by=current_admin['user_id'],
            version=test_request.version
        )
        
        return PromptTestResultSchema(
            test_id=test_result.test_id,
            template_id=test_result.template_id,
            version_id=test_result.version_id,
            input_data=test_result.input_data,
            rendered_prompt=test_result.rendered_prompt,
            test_response=test_result.test_response,
            execution_time_ms=test_result.execution_time_ms,
            success=test_result.success,
            error_message=test_result.error_message,
            metrics=test_result.metrics,
            tested_by=test_result.tested_by,
            tested_at=test_result.tested_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to test prompt", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao testar prompt: {str(e)}"
        )

@router.post("/templates/{template_id}/validate", response_model=PromptValidationSchema)
async def validate_prompt(
    template_id: str,
    current_admin = Depends(require_permission("agents:read"))
):
    """Validar estrutura e variáveis do prompt"""
    try:
        template = await prompt_editor_service.get_template(template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' não encontrado"
            )
        
        # Usar método interno de validação
        validation_result = prompt_editor_service._validate_prompt_content(
            template.content,
            template.variables
        )
        
        return PromptValidationSchema(
            valid=validation_result['valid'],
            errors=validation_result['errors'],
            warnings=validation_result['warnings'],
            content_variables=validation_result['content_variables'],
            defined_variables=validation_result['defined_variables'],
            required_variables=validation_result['required_variables']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to validate prompt", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao validar prompt: {str(e)}"
        )

# Version Management Endpoints
@router.get("/templates/{template_id}/versions", response_model=List[PromptVersionSchema])
async def get_template_versions(
    template_id: str,
    current_admin = Depends(require_permission("agents:read"))
):
    """Obter versões de um template"""
    try:
        versions = await prompt_editor_service.get_template_versions(template_id)
        
        return [
            PromptVersionSchema(
                version_id=version.version_id,
                template_id=version.template_id,
                version_number=version.version_number,
                content=version.content,
                variables=[
                    {
                        "name": var.name,
                        "type": var.type,
                        "description": var.description,
                        "required": var.required,
                        "default_value": var.default_value,
                        "validation_pattern": var.validation_pattern,
                        "min_length": var.min_length,
                        "max_length": var.max_length,
                        "options": var.options
                    }
                    for var in version.variables
                ],
                changelog=version.changelog,
                created_by=version.created_by,
                created_at=version.created_at,
                is_active=version.is_active
            )
            for version in versions
        ]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to get template versions", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter versões: {str(e)}"
        )

@router.get("/templates/{template_id}/test-results", response_model=List[PromptTestResultSchema])
async def get_template_test_results(
    template_id: str,
    limit: int = Query(20, ge=1, le=100, description="Limite de resultados"),
    current_admin = Depends(require_permission("agents:read"))
):
    """Obter resultados de teste de um template"""
    try:
        test_results = await prompt_editor_service.get_template_test_results(
            template_id=template_id,
            limit=limit
        )
        
        return [
            PromptTestResultSchema(
                test_id=result.test_id,
                template_id=result.template_id,
                version_id=result.version_id,
                input_data=result.input_data,
                rendered_prompt=result.rendered_prompt,
                test_response=result.test_response,
                execution_time_ms=result.execution_time_ms,
                success=result.success,
                error_message=result.error_message,
                metrics=result.metrics,
                tested_by=result.tested_by,
                tested_at=result.tested_at
            )
            for result in test_results
        ]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to get test results", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter resultados de teste: {str(e)}"
        )

# Analytics and Management Endpoints
@router.get("/templates/{template_id}/analytics", response_model=PromptAnalyticsSchema)
async def get_template_analytics(
    template_id: str,
    current_admin = Depends(require_permission("analytics:read"))
):
    """Obter analytics de um template"""
    try:
        analytics = await prompt_editor_service.get_template_analytics(template_id)
        
        return PromptAnalyticsSchema(**analytics)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to get template analytics", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter analytics: {str(e)}"
        )

@router.post("/templates/{template_id}/clone", response_model=PromptTemplateSchema)
async def clone_template(
    template_id: str,
    clone_request: PromptCloneRequestSchema,
    current_admin = Depends(require_permission("agents:write"))
):
    """Clonar template existente"""
    try:
        cloned_template = await prompt_editor_service.clone_template(
            template_id=template_id,
            new_name=clone_request.new_name,
            created_by=current_admin['user_id'],
            modifications=clone_request.modifications
        )
        
        return PromptTemplateSchema(
            template_id=cloned_template.template_id,
            name=cloned_template.name,
            description=cloned_template.description,
            category=cloned_template.category,
            type=cloned_template.type,
            content=cloned_template.content,
            variables=[
                {
                    "name": var.name,
                    "type": var.type,
                    "description": var.description,
                    "required": var.required,
                    "default_value": var.default_value,
                    "validation_pattern": var.validation_pattern,
                    "min_length": var.min_length,
                    "max_length": var.max_length,
                    "options": var.options
                }
                for var in cloned_template.variables
            ],
            tags=cloned_template.tags,
            version=cloned_template.version,
            status=cloned_template.status,
            created_by=cloned_template.created_by,
            created_at=cloned_template.created_at,
            updated_at=cloned_template.updated_at,
            usage_count=cloned_template.usage_count,
            rating=cloned_template.rating,
            metadata=cloned_template.metadata
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to clone template", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao clonar template: {str(e)}"
        )

@router.get("/templates/{template_id}/export")
async def export_template(
    template_id: str,
    current_admin = Depends(require_permission("agents:read"))
):
    """Exportar template para JSON"""
    try:
        template_data = await prompt_editor_service.export_template(template_id)
        
        return JSONResponse(
            content=template_data,
            headers={
                "Content-Disposition": f"attachment; filename=template_{template_id}.json"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to export template", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao exportar template: {str(e)}"
        )

@router.post("/templates/import", response_model=PromptTemplateSchema)
async def import_template(
    import_request: PromptImportRequestSchema,
    current_admin = Depends(require_permission("agents:write"))
):
    """Importar template de JSON"""
    try:
        imported_template = await prompt_editor_service.import_template(
            template_data=import_request.template_data,
            imported_by=current_admin['user_id'],
            overwrite=import_request.overwrite
        )
        
        return PromptTemplateSchema(
            template_id=imported_template.template_id,
            name=imported_template.name,
            description=imported_template.description,
            category=imported_template.category,
            type=imported_template.type,
            content=imported_template.content,
            variables=[
                {
                    "name": var.name,
                    "type": var.type,
                    "description": var.description,
                    "required": var.required,
                    "default_value": var.default_value,
                    "validation_pattern": var.validation_pattern,
                    "min_length": var.min_length,
                    "max_length": var.max_length,
                    "options": var.options
                }
                for var in imported_template.variables
            ],
            tags=imported_template.tags,
            version=imported_template.version,
            status=imported_template.status,
            created_by=imported_template.created_by,
            created_at=imported_template.created_at,
            updated_at=imported_template.updated_at,
            usage_count=imported_template.usage_count,
            rating=imported_template.rating,
            metadata=imported_template.metadata
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to import template", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao importar template: {str(e)}"
        )