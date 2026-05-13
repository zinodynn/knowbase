"""
版本管理 Pydantic Schema
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VersionCreate(BaseModel):
    """创建版本请求"""

    description: str = Field(..., min_length=1, max_length=500, description="版本描述")
    tags: Optional[str] = Field(None, max_length=200, description="版本标签，如 v1.0, stable")


class VersionSnapshotItem(BaseModel):
    """版本快照项"""

    id: str = Field(..., description="快照 ID")
    document_id: Optional[str] = Field(None, description="文档 ID")
    document_snapshot: Dict[str, Any] = Field(..., description="文档快照数据")
    chunk_ids: List[str] = Field(default_factory=list, description="分块 ID 列表")
    created_at: Optional[str] = Field(None, description="创建时间")


class VersionResponse(BaseModel):
    """版本列表响应"""

    id: str = Field(..., description="版本 ID")
    kb_id: str = Field(..., description="知识库 ID")
    version: int = Field(..., description="版本号")
    description: Optional[str] = Field(None, description="版本描述")
    document_count: int = Field(0, description="文档数量")
    chunk_count: int = Field(0, description="分块数量")
    is_active: bool = Field(False, description="是否为当前激活版本")
    tags: Optional[str] = Field(None, description="版本标签")
    created_by: Optional[str] = Field(None, description="创建者 ID")
    created_at: Optional[str] = Field(None, description="创建时间")


class VersionListResponse(BaseModel):
    """版本列表响应（分页）"""

    items: List[VersionResponse] = Field(..., description="版本列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


class VersionDetailResponse(BaseModel):
    """版本详情响应（含快照）"""

    id: str = Field(..., description="版本 ID")
    kb_id: str = Field(..., description="知识库 ID")
    version: int = Field(..., description="版本号")
    description: Optional[str] = Field(None, description="版本描述")
    commit_hash: Optional[str] = Field(None, description="Git/SVN 提交哈希")
    document_count: int = Field(0, description="文档数量")
    chunk_count: int = Field(0, description="分块数量")
    is_active: bool = Field(False, description="是否为当前激活版本")
    tags: Optional[str] = Field(None, description="版本标签")
    snapshot_data: Optional[Dict[str, Any]] = Field(None, description="快照摘要数据")
    created_by: Optional[str] = Field(None, description="创建者 ID")
    created_at: Optional[str] = Field(None, description="创建时间")
    snapshots: List[VersionSnapshotItem] = Field(
        default_factory=list, description="文档快照列表"
    )


class VersionCompareDoc(BaseModel):
    """版本对比 - 文档变化项"""

    document_id: str = Field(..., description="文档 ID")
    file_name: str = Field(..., description="文件名")


class VersionCompareModifiedDoc(BaseModel):
    """版本对比 - 修改文档项"""

    document_id: str = Field(..., description="文档 ID")
    file_name: str = Field(..., description="文件名")
    old_hash: Optional[str] = Field(None, description="旧内容哈希")
    new_hash: Optional[str] = Field(None, description="新内容哈希")


class VersionCompareVersionInfo(BaseModel):
    """版本对比 - 版本基本信息"""

    id: str = Field(..., description="版本 ID")
    version: int = Field(..., description="版本号")
    description: Optional[str] = Field(None, description="版本描述")
    document_count: int = Field(0, description="文档数量")
    chunk_count: int = Field(0, description="分块数量")


class VersionCompareSummary(BaseModel):
    """版本对比 - 差异摘要"""

    added_count: int = Field(0, description="新增文档数")
    removed_count: int = Field(0, description="删除文档数")
    modified_count: int = Field(0, description="修改文档数")
    total_changes: int = Field(0, description="总变更数")


class VersionCompareResponse(BaseModel):
    """版本对比响应"""

    version_1: VersionCompareVersionInfo = Field(..., description="版本1信息")
    version_2: VersionCompareVersionInfo = Field(..., description="版本2信息")
    added_docs: List[VersionCompareDoc] = Field(default_factory=list, description="新增文档")
    removed_docs: List[VersionCompareDoc] = Field(default_factory=list, description="删除文档")
    modified_docs: List[VersionCompareModifiedDoc] = Field(
        default_factory=list, description="修改文档"
    )
    summary: VersionCompareSummary = Field(..., description="差异摘要")
