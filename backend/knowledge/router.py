"""
知识库 API 路由
- 文档上传与入库
- 知识库统计
- 清空知识库
"""
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
import tempfile
import os

from backend.auth.models import User
from backend.auth.rbac import get_current_user, require_role
from .rag_pipeline import get_rag_pipeline, RAGConfig

logger = logging.getLogger(__name__)

knowledge_router = APIRouter(prefix="/knowledge", tags=["知识库"])


@knowledge_router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_role("admin")),
):
    """上传文档到知识库（仅管理员）"""
    pipeline = get_rag_pipeline()
    results = []
    temp_files = []

    try:
        for file in files:
            # 验证文件类型
            allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.csv'}
            suffix = os.path.splitext(file.filename)[1].lower()
            if suffix not in allowed_extensions:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": f"不支持的文件类型: {suffix}",
                })
                continue

            # 读取文件并检查大小（限制 50MB）
            content = await file.read()
            max_file_size = 50 * 1024 * 1024
            if len(content) > max_file_size:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": "文件过大，最大支持 50MB",
                })
                continue

            # 保存临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                temp_path = tmp.name
                temp_files.append(temp_path)

            # 入库
            result = await pipeline.ingest_file(temp_path)
            result["filename"] = file.filename
            results.append(result)

        # 计算总数
        total_chunks = sum(r.get("chunks", 0) for r in results if r["success"])
        success_count = sum(1 for r in results if r["success"])

        return {
            "message": f"成功处理 {success_count}/{len(files)} 个文件，共 {total_chunks} 个文档块",
            "total_chunks": total_chunks,
            "details": results,
        }

    except Exception as e:
        logger.exception(f"上传文档失败: {e}")
        raise HTTPException(status_code=400, detail="处理文件失败，请稍后再试")

    finally:
        # 清理临时文件
        for temp_path in temp_files:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


@knowledge_router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user)):
    """获取知识库统计"""
    pipeline = get_rag_pipeline()
    return pipeline.get_stats()


@knowledge_router.delete("/clear")
async def clear_knowledge(current_user: User = Depends(require_role("admin"))):
    """清空知识库（仅管理员）"""
    pipeline = get_rag_pipeline()
    await pipeline.clear()
    return {"message": "知识库已清空"}


@knowledge_router.post("/search")
async def search_knowledge(
    query: str,
    top_k: int = 5,
    current_user: User = Depends(get_current_user),
):
    """检索知识库"""
    pipeline = get_rag_pipeline()
    results = await pipeline.search(query, top_k=top_k)

    return {
        "query": query,
        "results": [
            {
                "content": r.content,
                "metadata": r.metadata,
                "score": r.score,
            }
            for r in results
        ],
    }
