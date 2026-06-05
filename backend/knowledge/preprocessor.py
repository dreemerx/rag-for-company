"""
数据清洗与预处理模块
- 噪声去除：页眉页脚、页码、水印、特殊字符
- 文本标准化：全角半角、空格、换行
- 元数据提取：标题、日期、版本
"""
import re
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from .chunker import Document


class TextCleaner:
    """文本清洗器"""

    # 页眉页脚模式
    HEADER_FOOTER_PATTERNS = [
        r'第\s*\d+\s*页.*?共\s*\d+\s*页',
        r'Page\s*\d+\s*of\s*\d+',
        r'©.*?版权所有',
        r'Copyright.*?\d{4}',
        r'confidential|机密|内部文件|仅供内部使用',
        r'^\s*-\s*\d+\s*-\s*$',  # 页码格式 -1-
        r'^\s*\d+\s*/\s*\d+\s*$',  # 页码格式 1/10
    ]

    # 噪声字符模式
    NOISE_PATTERNS = [
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]',  # 控制字符
        r'[�]',  # 替换字符
        r'[□■◆◇○●]',  # 特殊符号（保留常用标点）
    ]

    @staticmethod
    def clean(text: str) -> str:
        """清洗文本"""
        if not text:
            return ""

        # 去除页眉页脚
        for pattern in TextCleaner.HEADER_FOOTER_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # 去除噪声字符
        for pattern in TextCleaner.NOISE_PATTERNS:
            text = re.sub(pattern, '', text)

        # 去除多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\t+', ' ', text)

        # 去除行首行尾空白
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()


class TextNormalizer:
    """文本标准化器"""

    # 全角字符映射（数字和字母）
    FULLWIDTH_OFFSET = 0xFEE0

    @staticmethod
    def normalize(text: str) -> str:
        """标准化文本"""
        if not text:
            return ""

        # 全角转半角（数字和字母）
        result = []
        for char in text:
            code = ord(char)
            if 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - TextNormalizer.FULLWIDTH_OFFSET))
            elif code == 0x3000:  # 全角空格
                result.append(' ')
            else:
                result.append(char)
        text = ''.join(result)

        # 统一引号
        text = text.replace('“', '"').replace('”', '"')  # 中文双引号
        text = text.replace('‘', "'").replace('’', "'")  # 中文单引号

        # 统一连字符
        text = re.sub(r'[‐‑‒–—―]', '-', text)

        # 统一省略号
        text = text.replace('…', '...').replace('⋯', '...')

        # 去除多余标点
        text = re.sub(r'[。]{2,}', '。', text)
        text = re.sub(r'[！]{2,}', '！', text)
        text = re.sub(r'[？]{2,}', '？', text)

        return text.strip()


class MetadataExtractor:
    """元数据提取器"""

    # 日期模式
    DATE_PATTERNS = [
        r'20\d{2}[年\-/\.]\d{1,2}[月\-/\.]\d{1,2}[日号]?',
        r'\d{4}[年\-/\.]\d{1,2}[月\-/\.]\d{1,2}',
    ]

    # 版本模式
    VERSION_PATTERNS = [
        r'[Vv]\d+[\.\d]*',
        r'第.*?版',
        r'版本.*?\d+',
        r'Rev\.\s*\d+',
    ]

    # 标题模式（中文序号）
    TITLE_PATTERNS = [
        r'^第[一二三四五六七八九十百千]+[章篇节]',
        r'^[一二三四五六七八九十]+[、．.]',
        r'^\d+[\.\、]\s*\S+',  # 1. xxx 或 1、xxx
    ]

    @staticmethod
    def extract(file_path: str, text: str) -> Dict[str, Any]:
        """提取元数据"""
        path = Path(file_path)

        # 提取标题
        title = MetadataExtractor._extract_title(text, path.stem)

        # 提取日期
        date_str = MetadataExtractor._extract_date(text)

        # 提取版本
        version = MetadataExtractor._extract_version(text)

        return {
            'source': str(path),
            'filename': path.name,
            'file_type': path.suffix.lower(),
            'title': title,
            'date': date_str,
            'version': version,
            'upload_time': datetime.now().isoformat(),
            'char_count': len(text),
        }

    @staticmethod
    def _extract_title(text: str, fallback: str) -> str:
        """提取标题"""
        lines = text.strip().split('\n')

        # 尝试从内容中提取标题
        for line in lines[:10]:  # 只看前10行
            line = line.strip()
            if not line:
                continue

            # 匹配标题模式
            for pattern in MetadataExtractor.TITLE_PATTERNS:
                if re.match(pattern, line):
                    return line[:100]  # 限制长度

            # 如果第一行较短，可能是标题
            if len(line) < 50 and not line.endswith('。'):
                return line

        return fallback

    @staticmethod
    def _extract_date(text: str) -> str:
        """提取日期"""
        for pattern in MetadataExtractor.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group()
        return None

    @staticmethod
    def _extract_version(text: str) -> str:
        """提取版本"""
        for pattern in MetadataExtractor.VERSION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group()
        return None


class DocumentPreprocessor:
    """文档预处理器"""

    def __init__(self):
        self.cleaner = TextCleaner()
        self.normalizer = TextNormalizer()
        self.metadata_extractor = MetadataExtractor()

    def preprocess(self, file_path: str, raw_text: str) -> Dict[str, Any]:
        """
        完整预处理流程

        Args:
            file_path: 文件路径
            raw_text: 原始文本

        Returns:
            {
                'cleaned_text': str,
                'metadata': dict,
                'char_count': int
            }
        """
        # 1. 清洗
        cleaned = self.cleaner.clean(raw_text)

        # 2. 标准化
        normalized = self.normalizer.normalize(cleaned)

        # 3. 提取元数据
        metadata = self.metadata_extractor.extract(file_path, normalized)

        return {
            'cleaned_text': normalized,
            'metadata': metadata,
            'char_count': len(normalized),
        }

    def preprocess_batch(self, documents: List[Document]) -> List[Document]:
        """
        批量预处理

        Args:
            documents: 原始文档列表

        Returns:
            清洗后的文档列表
        """
        processed = []
        for doc in documents:
            result = self.preprocess(
                doc.metadata.get('source', 'unknown'),
                doc.page_content
            )

            # 跳过过短的文档
            if result['char_count'] < 10:
                continue

            # 合并元数据
            metadata = {**doc.metadata, **result['metadata']}

            processed.append(Document(
                page_content=result['cleaned_text'],
                metadata=metadata
            ))

        return processed


# 单例
_preprocessor = None


def get_preprocessor() -> DocumentPreprocessor:
    """获取预处理器单例"""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = DocumentPreprocessor()
    return _preprocessor
