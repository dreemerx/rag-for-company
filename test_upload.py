"""
测试文档上传脚本
- 加载测试文档
- 预处理、分块、Embedding
- 上传到 Milvus
"""
import asyncio
import sys
import os
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.knowledge.document_loader import DocumentLoader
from backend.knowledge.preprocessor import get_preprocessor
from backend.knowledge.chunker import get_chunker
from backend.knowledge.embedding import get_embedding_manager
from backend.knowledge.vector_store import get_vector_store


async def upload_test_docs():
    """上传测试文档"""
    print("=" * 60)
    print("开始上传测试文档")
    print("=" * 60)

    # 初始化组件
    loader = DocumentLoader()
    preprocessor = get_preprocessor()
    chunker = get_chunker(chunk_size=500, chunk_overlap=50)
    embedding_manager = get_embedding_manager()
    vector_store = get_vector_store()

    # 测试文档目录
    test_docs_dir = "./test_docs"

    if not os.path.exists(test_docs_dir):
        print(f"错误：测试文档目录不存在: {test_docs_dir}")
        return

    # 获取所有文档
    all_files = []
    for filename in os.listdir(test_docs_dir):
        filepath = os.path.join(test_docs_dir, filename)
        if os.path.isfile(filepath):
            all_files.append(filepath)

    print(f"\n找到 {len(all_files)} 个文档:")
    for f in all_files:
        print(f"  - {os.path.basename(f)}")

    # 处理每个文档
    total_chunks = 0
    start_time = time.time()

    for filepath in all_files:
        filename = os.path.basename(filepath)
        print(f"\n处理: {filename}")
        print("-" * 40)

        try:
            # 1. 加载文档
            print("  1. 加载文档...")
            raw_docs = await loader.load_file(filepath)
            print(f"     加载完成: {len(raw_docs)} 个文档")

            # 2. 预处理
            print("  2. 预处理（清洗、标准化）...")
            processed_docs = preprocessor.preprocess_batch(raw_docs)
            print(f"     预处理完成: {len(processed_docs)} 个文档")

            # 3. 分块
            print("  3. 语义分块...")
            all_chunks = []
            for doc in processed_docs:
                chunks = chunker.chunk(doc.page_content, doc.metadata)
                all_chunks.extend(chunks)
            print(f"     分块完成: {len(all_chunks)} 个块")

            # 4. 生成 Embedding
            print("  4. 生成 Embedding...")
            texts = [chunk.page_content for chunk in all_chunks]
            dense_embeddings = embedding_manager.embed_dense(texts)
            print(f"     Embedding 完成: {len(dense_embeddings)} 个向量")

            # 5. 上传到 Milvus
            print("  5. 上传到 Milvus...")
            sparse_embeddings = [{}] * len(all_chunks)  # 空稀疏向量
            count = await vector_store.add_documents(
                documents=all_chunks,
                dense_embeddings=dense_embeddings,
                sparse_embeddings=sparse_embeddings,
            )
            print(f"     上传完成: {count} 个文档")

            total_chunks += count

        except Exception as e:
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("上传完成")
    print("=" * 60)
    print(f"总文档数: {len(all_files)}")
    print(f"总块数: {total_chunks}")
    print(f"耗时: {elapsed:.2f} 秒")
    print(f"向量库文档总数: {vector_store.get_count()}")


async def test_search():
    """测试检索"""
    print("\n" + "=" * 60)
    print("测试检索")
    print("=" * 60)

    embedding_manager = get_embedding_manager()
    vector_store = get_vector_store()

    # 测试查询
    test_queries = [
        "年假政策是什么？",
        "报销流程怎么走？",
        "会议室怎么预订？",
        "迟到怎么处理？",
        "信息安全有什么要求？",
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 40)

        # 生成查询向量
        dense_vector, _ = embedding_manager.embed_query(query)

        # 检索
        results = await vector_store.search(dense_vector, top_k=3)

        if results:
            for i, result in enumerate(results, 1):
                print(f"  [{i}] 相关度: {result.score:.3f}")
                print(f"      来源: {result.metadata.get('filename', '未知')}")
                print(f"      内容: {result.content[:100]}...")
        else:
            print("  未找到相关结果")


async def main():
    """主函数"""
    await upload_test_docs()
    await test_search()


if __name__ == "__main__":
    asyncio.run(main())
