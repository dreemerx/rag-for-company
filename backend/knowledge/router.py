from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List

from backend.auth.models import User
from backend.auth.rbac import get_current_user, require_role
from .vector_store import get_vector_store
from .document_loader import DocumentLoader

knowledge_router = APIRouter(prefix="/knowledge", tags=["知识库"])


@knowledge_router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传文档到知识库"""
    loader = DocumentLoader()
    vector_store = get_vector_store()
    total_docs = 0

    for file in files:
        # 保存临时文件
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            # 加载文档
            docs = await loader.load_file(temp_path)
            # 添加到向量库
            count = await vector_store.add_documents(docs)
            total_docs += count
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"处理文件 {file.filename} 失败: {str(e)}")

    return {
        "message": f"成功导入 {total_docs} 条文档",
        "total": total_docs,
    }


@knowledge_router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user)):
    """获取知识库统计"""
    vector_store = get_vector_store()
    return {
        "document_count": vector_store.get_count(),
    }


@knowledge_router.delete("/clear")
async def clear_knowledge(current_user: User = Depends(require_role("admin"))):
    """清空知识库（仅管理员）"""
    vector_store = get_vector_store()
    await vector_store.clear()
    return {"message": "知识库已清空"}
