"""
语义分块模块
- 按语义边界切分文档
- 支持父子文档策略
- 保持上下文连贯性
"""
import re
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class Document:
    """文档数据结构"""
    page_content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ChunkConfig:
    """分块配置"""
    chunk_size: int = 500  # 目标块大小（字符数）
    chunk_overlap: int = 50  # 重叠大小
    min_chunk_size: int = 50  # 最小块大小
    max_chunk_size: int = 1000  # 最大块大小
    separators: Optional[List[str]] = None  # 自定义分隔符

    def __post_init__(self):
        if self.separators is None:
            # 默认分隔符优先级
            self.separators = [
                '\n# ',  # Markdown 一级标题
                '\n## ',  # Markdown 二级标题
                '\n### ',  # Markdown 三级标题
                '\n#### ',  # Markdown 四级标题
                '\n第[一二三四五六七八九十百千]+[章篇节条]',  # 中文章节
                '\n\d+[\.\、]',  # 数字编号
                '\n[一二三四五六七八九十]+[、．.]',  # 中文编号
                '\n\n',  # 段落分隔
                '\n',  # 换行
                '。',  # 句号
                '；',  # 分号
                '！',  # 感叹号
                '？',  # 问号
                '. ',  # 英文句号
            ]


class SemanticChunker:
    """语义分块器"""

    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()

    def chunk(self, text: str, metadata: Optional[dict] = None) -> List[Document]:
        """
        对文本进行语义分块

        Args:
            text: 输入文本
            metadata: 元数据

        Returns:
            文档块列表
        """
        if not text or len(text) < self.config.min_chunk_size:
            return [Document(page_content=text, metadata=metadata or {})]

        metadata = metadata or {}

        # 使用递归分块
        raw_chunks = self._split_text(text, self.config.separators)

        # 合并过小的块
        merged_chunks = self._merge_small_chunks(raw_chunks)

        # 拆分过大的块
        final_chunks = []
        for chunk in merged_chunks:
            if len(chunk) > self.config.max_chunk_size:
                final_chunks.extend(self._split_large_chunk(chunk))
            else:
                final_chunks.append(chunk)

        # 添加重叠
        if self.config.chunk_overlap > 0:
            final_chunks = self._add_overlap(final_chunks)

        # 构建文档对象
        documents = []
        for i, chunk in enumerate(final_chunks):
            chunk_metadata = {
                **metadata,
                'chunk_index': i,
                'total_chunks': len(final_chunks),
                'chunk_size': len(chunk),
            }
            documents.append(Document(
                page_content=chunk,
                metadata=chunk_metadata
            ))

        return documents

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """递归分块"""
        if not separators:
            # 没有更多分隔符，按字符数切分
            return self._split_by_size(text)

        sep = separators[0]
        remaining_seps = separators[1:]

        # 检查是否包含当前分隔符
        if not re.search(sep, text):
            return self._split_text(text, remaining_seps)

        # 按分隔符切分
        parts = re.split(f'({sep})', text)

        # 合并分隔符到前一个块
        merged_parts = []
        for i, part in enumerate(parts):
            if re.match(sep, part) and merged_parts:
                # 分隔符合并到前一个块
                merged_parts[-1] += part
            elif part.strip():
                merged_parts.append(part)

        # 处理每个部分
        chunks = []
        for part in merged_parts:
            if len(part) <= self.config.chunk_size:
                chunks.append(part)
            else:
                # 递归处理过大的部分
                chunks.extend(self._split_text(part, remaining_seps))

        return chunks

    def _split_by_size(self, text: str) -> List[str]:
        """按字符数切分"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.config.chunk_size
            chunks.append(text[start:end])
            start = end - self.config.chunk_overlap
        return chunks

    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """合并过小的块"""
        if not chunks:
            return []

        merged = []
        current = chunks[0]

        for i in range(1, len(chunks)):
            # 如果当前块加上下一个块不超过目标大小，合并
            if len(current) + len(chunks[i]) <= self.config.chunk_size:
                current += chunks[i]
            else:
                # 当前块够大，保存并开始新块
                if len(current) >= self.config.min_chunk_size:
                    merged.append(current)
                else:
                    # 当前块太小，强制合并到下一个
                    current += chunks[i]
                current = chunks[i]

        # 处理最后一个块
        if current:
            if merged and len(current) < self.config.min_chunk_size:
                # 最后一个块太小，合并到前一个
                merged[-1] += current
            else:
                merged.append(current)

        return merged

    def _split_large_chunk(self, chunk: str) -> List[str]:
        """拆分过大的块"""
        chunks = []
        start = 0
        while start < len(chunk):
            end = min(start + self.config.chunk_size, len(chunk))
            chunks.append(chunk[start:end])
            start = end
        return chunks

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """添加重叠"""
        if len(chunks) <= 1:
            return chunks

        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            # 从前一个块取末尾作为重叠
            prev_tail = chunks[i-1][-self.config.chunk_overlap:]
            overlapped.append(prev_tail + chunks[i])

        return overlapped


class ParentChildChunker:
    """
    父子文档分块器
    - 小块用于检索（提高精度）
    - 大块用于生成（保留上下文）
    """

    def __init__(
        self,
        parent_size: int = 1000,
        child_size: int = 200,
        child_overlap: int = 50
    ):
        self.parent_chunker = SemanticChunker(ChunkConfig(
            chunk_size=parent_size,
            chunk_overlap=0
        ))
        self.child_chunker = SemanticChunker(ChunkConfig(
            chunk_size=child_size,
            chunk_overlap=child_overlap,
            min_chunk_size=30
        ))

    def chunk(self, text: str, metadata: Optional[dict] = None) -> List[Document]:
        """
        生成父子文档

        Returns:
            子文档列表，每个子文档包含 parent_id 指向父文档
        """
        metadata = metadata or {}

        # 先生成父文档
        parent_docs = self.parent_chunker.chunk(text, metadata)

        all_child_docs = []
        for parent_idx, parent_doc in enumerate(parent_docs):
            # 生成子文档
            child_docs = self.child_chunker.chunk(
                parent_doc.page_content,
                {**parent_doc.metadata, 'parent_index': parent_idx}
            )

            # 为子文档添加父文档内容（用于生成时提供上下文）
            for child_doc in child_docs:
                child_doc.metadata['parent_content'] = parent_doc.page_content
                all_child_docs.append(child_doc)

        return all_child_docs


# 工厂函数
def get_chunker(
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    use_parent_child: bool = False,
    parent_size: int = 1000,
    child_size: int = 200
):
    """获取分块器"""
    if use_parent_child:
        return ParentChildChunker(
            parent_size=parent_size,
            child_size=child_size,
            child_overlap=chunk_overlap
        )
    else:
        return SemanticChunker(ChunkConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        ))
