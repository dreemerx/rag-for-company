"""
知识库模块
- 文档加载与预处理
- 语义分块
- Embedding 生成
- 向量数据库（Milvus）
- 混合检索
- HyDE 查询改写
- RAG 流水线
"""

from .chunker import Document, SemanticChunker, ParentChildChunker, ChunkConfig
from .preprocessor import DocumentPreprocessor, TextCleaner, TextNormalizer
from .embedding import EmbeddingManager, get_embedding_manager
from .vector_store import MilvusVectorStore, SearchResult, get_vector_store
from .reranker import Reranker, CrossEncoderReranker, SimpleReranker, get_reranker
from .hybrid_search import HybridSearcher, SimpleHybridSearcher, get_hybrid_searcher
from .hyde import HyDEGenerator, HyDESearcher, get_hyde_searcher
from .rag_pipeline import RAGPipeline, RAGConfig, get_rag_pipeline
from .document_loader import DocumentLoader
from .router import knowledge_router

__all__ = [
    # 数据结构
    "Document",
    "SearchResult",
    "ChunkConfig",
    "RAGConfig",

    # 核心组件
    "SemanticChunker",
    "ParentChildChunker",
    "DocumentPreprocessor",
    "TextCleaner",
    "TextNormalizer",
    "EmbeddingManager",
    "MilvusVectorStore",
    "Reranker",
    "CrossEncoderReranker",
    "SimpleReranker",
    "HybridSearcher",
    "SimpleHybridSearcher",
    "HyDEGenerator",
    "HyDESearcher",
    "RAGPipeline",
    "DocumentLoader",

    # 工厂函数
    "get_embedding_manager",
    "get_vector_store",
    "get_reranker",
    "get_hybrid_searcher",
    "get_hyde_searcher",
    "get_rag_pipeline",

    # 路由
    "knowledge_router",
]
