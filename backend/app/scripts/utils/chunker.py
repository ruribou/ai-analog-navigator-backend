"""
テキストをチャンクに分割するモジュール
"""
from typing import List, Dict, Any
import tiktoken


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    テキストのトークン数をカウント
    
    Args:
        text: カウント対象のテキスト
        encoding_name: エンコーディング名（デフォルト: cl100k_base）
    
    Returns:
        トークン数
    """
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))


def chunk_text(
    text: str,
    sections: List[Dict[str, Any]] = None,
    chunk_size_tokens: int = 400,
    overlap_tokens: int = 80,
    encoding_name: str = "cl100k_base"
) -> List[Dict[str, Any]]:
    """
    テキストをチャンクに分割（heading-aware）
    
    Args:
        text: 分割対象のテキスト
        sections: セクション情報（heading, level, contentを含む辞書のリスト）
        chunk_size_tokens: チャンクサイズ（トークン数）
        overlap_tokens: オーバーラップサイズ（トークン数）
        encoding_name: エンコーディング名
    
    Returns:
        チャンクのリスト（各要素は辞書）
    """
    encoding = tiktoken.get_encoding(encoding_name)
    chunks = []
    
    if sections:
        # セクションベースの分割
        chunks = chunk_by_sections(sections, chunk_size_tokens, overlap_tokens, encoding)
    else:
        # シンプルな分割
        chunks = chunk_simple(text, chunk_size_tokens, overlap_tokens, encoding)
    
    return chunks


def chunk_by_sections(
    sections: List[Dict[str, Any]],
    chunk_size_tokens: int,
    overlap_tokens: int,
    encoding
) -> List[Dict[str, Any]]:
    """
    セクション構造を考慮したチャンク分割
    
    Args:
        sections: セクション情報のリスト
        chunk_size_tokens: チャンクサイズ（トークン数）
        overlap_tokens: オーバーラップサイズ（トークン数）
        encoding: tiktokenのエンコーディング
    
    Returns:
        チャンクのリスト
    """
    chunks = []
    heading_stack = []  # 見出しのスタック
    current_chunk_text = []
    current_chunk_tokens = 0
    chunk_index = 0
    
    for section in sections:
        heading = section.get('heading', '')
        level = section.get('level', 1)
        content = section.get('content', '')
        
        # 見出しスタックを更新
        while heading_stack and heading_stack[-1]['level'] >= level:
            heading_stack.pop()
        
        if heading:
            heading_stack.append({'level': level, 'text': heading})
        
        # 見出しパスを構築
        heading_path = [h['text'] for h in heading_stack]
        
        # セクション全体のテキスト
        section_text = f"{heading}\n{content}" if heading else content
        section_tokens = len(encoding.encode(section_text))
        
        # 現在のチャンクに追加できるか確認
        if current_chunk_tokens + section_tokens <= chunk_size_tokens:
            current_chunk_text.append(section_text)
            current_chunk_tokens += section_tokens
        else:
            # 現在のチャンクを保存
            if current_chunk_text:
                chunk_text = '\n\n'.join(current_chunk_text)
                chunks.append({
                    'text': chunk_text,
                    'heading_path': heading_path.copy(),
                    'chunk_index': chunk_index,
                    'token_count': count_tokens(chunk_text)
                })
                chunk_index += 1
            
            # セクションが大きすぎる場合は分割
            if section_tokens > chunk_size_tokens:
                # セクションを細かく分割
                sub_chunks = split_large_section(
                    section_text,
                    heading_path.copy(),
                    chunk_size_tokens,
                    overlap_tokens,
                    encoding,
                    chunk_index
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                current_chunk_text = []
                current_chunk_tokens = 0
            else:
                # 新しいチャンクを開始
                current_chunk_text = [section_text]
                current_chunk_tokens = section_tokens
    
    # 最後のチャンクを保存
    if current_chunk_text:
        chunk_text = '\n\n'.join(current_chunk_text)
        chunks.append({
            'text': chunk_text,
            'heading_path': heading_stack.copy() if heading_stack else [],
            'chunk_index': chunk_index,
            'token_count': count_tokens(chunk_text)
        })
    
    return chunks


def split_large_section(
    text: str,
    heading_path: List[str],
    chunk_size_tokens: int,
    overlap_tokens: int,
    encoding,
    start_index: int
) -> List[Dict[str, Any]]:
    """
    大きなセクションを複数のチャンクに分割
    
    Args:
        text: 分割対象のテキスト
        heading_path: 見出しパス
        chunk_size_tokens: チャンクサイズ（トークン数）
        overlap_tokens: オーバーラップサイズ（トークン数）
        encoding: tiktokenのエンコーディング
        start_index: 開始インデックス
    
    Returns:
        チャンクのリスト
    """
    chunks = []
    tokens = encoding.encode(text)
    
    start = 0
    chunk_index = start_index
    
    while start < len(tokens):
        end = min(start + chunk_size_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        
        chunks.append({
            'text': chunk_text,
            'heading_path': heading_path.copy(),
            'chunk_index': chunk_index,
            'token_count': len(chunk_tokens)
        })
        
        chunk_index += 1
        start = end - overlap_tokens if end < len(tokens) else end
    
    return chunks


def chunk_simple(
    text: str,
    chunk_size_tokens: int,
    overlap_tokens: int,
    encoding
) -> List[Dict[str, Any]]:
    """
    シンプルなチャンク分割（セクション情報なし）
    
    Args:
        text: 分割対象のテキスト
        chunk_size_tokens: チャンクサイズ（トークン数）
        overlap_tokens: オーバーラップサイズ（トークン数）
        encoding: tiktokenのエンコーディング
    
    Returns:
        チャンクのリスト
    """
    chunks = []
    tokens = encoding.encode(text)
    
    start = 0
    chunk_index = 0
    
    while start < len(tokens):
        end = min(start + chunk_size_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        
        chunks.append({
            'text': chunk_text,
            'heading_path': [],
            'chunk_index': chunk_index,
            'token_count': len(chunk_tokens)
        })
        
        chunk_index += 1
        start = end - overlap_tokens if end < len(tokens) else end
    
    return chunks

