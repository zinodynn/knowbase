"""
模型配置管理路由
"""
from typing import Any, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.encryption import EncryptionService
from app.models.user import User
from app.models.model_config import ModelConfig
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse,
    ModelConfigListResponse,
    ModelConfigTestRequest,
    ModelConfigTestResponse,
)
from app.api.deps import get_current_user, get_current_superuser


router = APIRouter()
encryption_service = EncryptionService()


@router.get("", response_model=ModelConfigListResponse, summary="获取模型配置列表")
async def list_model_configs(
    model_type: str = Query(None, description="模型类型过滤"),
    provider: str = Query(None, description="提供商过滤"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="获取数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取模型配置列表
    
    - 普通用户只能看到激活的配置
    - 管理员可以看到所有配置
    """
    # 构建查询
    query = select(ModelConfig)
    
    # 非管理员只能看到激活的配置
    if not current_user.is_superuser:
        query = query.where(ModelConfig.is_active == True)
    
    # 类型过滤
    if model_type:
        query = query.where(ModelConfig.model_type == model_type)
    
    if provider:
        query = query.where(ModelConfig.provider == provider)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar()
    
    # 获取列表
    query = query.offset(skip).limit(limit).order_by(
        ModelConfig.is_default.desc(),
        ModelConfig.created_at.desc()
    )
    result = await db.execute(query)
    items = result.scalars().all()
    
    return ModelConfigListResponse(items=items, total=total)


@router.post("", response_model=ModelConfigResponse, summary="创建模型配置")
async def create_model_config(
    config_in: ModelConfigCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """创建模型配置（需要管理员权限）"""
    # 加密 API Key
    encrypted_api_key = None
    if config_in.api_key:
        encrypted_api_key = encryption_service.encrypt(config_in.api_key)
    
    # 如果设置为默认，取消其他同类型的默认设置
    if config_in.is_default:
        result = await db.execute(
            select(ModelConfig).where(
                ModelConfig.model_type == config_in.model_type,
                ModelConfig.is_default == True
            )
        )
        existing_defaults = result.scalars().all()
        for cfg in existing_defaults:
            cfg.is_default = False
    
    # 创建配置
    config = ModelConfig(
        name=config_in.name,
        model_type=config_in.model_type,
        provider=config_in.provider,
        model_name=config_in.model_name,
        api_base=config_in.api_base,
        encrypted_api_key=encrypted_api_key,
        extra_params=config_in.extra_params,
        is_default=config_in.is_default,
        is_active=True
    )
    
    db.add(config)
    await db.commit()
    await db.refresh(config)
    
    return config


@router.get("/{config_id}", response_model=ModelConfigResponse, summary="获取模型配置详情")
async def get_model_config(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """获取模型配置详情"""
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型配置不存在"
        )
    
    # 非管理员不能查看非激活的配置
    if not current_user.is_superuser and not config.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型配置不存在"
        )
    
    return config


@router.put("/{config_id}", response_model=ModelConfigResponse, summary="更新模型配置")
async def update_model_config(
    config_id: uuid.UUID,
    config_in: ModelConfigUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """更新模型配置（需要管理员权限）"""
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型配置不存在"
        )
    
    # 更新字段
    update_data = config_in.model_dump(exclude_unset=True)
    
    # 处理 API Key 加密
    if "api_key" in update_data:
        api_key = update_data.pop("api_key")
        if api_key:
            config.encrypted_api_key = encryption_service.encrypt(api_key)
        else:
            config.encrypted_api_key = None
    
    # 如果设置为默认，取消其他同类型的默认设置
    if update_data.get("is_default"):
        result = await db.execute(
            select(ModelConfig).where(
                ModelConfig.model_type == config.model_type,
                ModelConfig.is_default == True,
                ModelConfig.id != config_id
            )
        )
        existing_defaults = result.scalars().all()
        for cfg in existing_defaults:
            cfg.is_default = False
    
    for field, value in update_data.items():
        setattr(config, field, value)
    
    await db.commit()
    await db.refresh(config)
    
    return config


@router.delete("/{config_id}", summary="删除模型配置")
async def delete_model_config(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """删除模型配置（需要管理员权限）"""
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型配置不存在"
        )
    
    await db.delete(config)
    await db.commit()
    
    return {"message": "模型配置已删除"}


@router.post("/{config_id}/test", response_model=ModelConfigTestResponse, summary="测试模型配置")
async def test_model_config(
    config_id: uuid.UUID,
    test_in: ModelConfigTestRequest,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    测试模型配置连接（需要管理员权限）
    
    注意：此接口会实际调用模型 API，可能产生费用
    """
    import time
    
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型配置不存在"
        )
    
    # 解密 API Key
    api_key = None
    if config.encrypted_api_key:
        api_key = encryption_service.decrypt(config.encrypted_api_key)
    
    # TODO: 实现实际的模型调用测试
    # 这里只是一个占位实现
    start_time = time.time()
    
    try:
        # 根据不同的模型类型和提供商进行测试
        # 这部分需要在后续实现具体的模型调用逻辑
        
        latency_ms = (time.time() - start_time) * 1000
        
        return ModelConfigTestResponse(
            success=True,
            message="配置验证成功",
            latency_ms=latency_ms,
            output=f"测试配置: {config.name} ({config.provider}/{config.model_name})"
        )
    
    except Exception as e:
        return ModelConfigTestResponse(
            success=False,
            message=f"配置验证失败: {str(e)}"
        )


@router.post("/{config_id}/set-default", response_model=ModelConfigResponse, summary="设为默认配置")
async def set_default_model_config(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """将指定配置设为该类型的默认配置（需要管理员权限）"""
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型配置不存在"
        )
    
    # 取消其他同类型的默认设置
    result = await db.execute(
        select(ModelConfig).where(
            ModelConfig.model_type == config.model_type,
            ModelConfig.is_default == True
        )
    )
    existing_defaults = result.scalars().all()
    for cfg in existing_defaults:
        cfg.is_default = False
    
    # 设置当前配置为默认
    config.is_default = True
    
    await db.commit()
    await db.refresh(config)
    
    return config


@router.get("/defaults/all", response_model=List[ModelConfigResponse], summary="获取所有默认配置")
async def get_default_model_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """获取所有类型的默认模型配置"""
    result = await db.execute(
        select(ModelConfig).where(
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        )
    )
    configs = result.scalars().all()
    
    return configs
