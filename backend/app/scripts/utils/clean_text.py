"""
HTMLからテキストを抽出・正規化するモジュール
"""
import re
from typing import Optional
from bs4 import BeautifulSoup


def clean_html_text(html: str, min_length: int = 200) -> Optional[str]:
    """
    HTMLから本文テキストを抽出・正規化
    
    Args:
        html: HTML文字列
        min_length: 最小文字数（これ未満の場合はNoneを返す）
    
    Returns:
        正規化されたテキスト、または None（短すぎる場合）
    """
    # BeautifulSoupでパース
    soup = BeautifulSoup(html, 'lxml')
    
    # 不要な要素を削除
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
        element.decompose()
    
    # サイト固有の不要要素を削除（クラス/IDベース）
    # 東京電機大学のサイト用
    for selector in [
        'class_=["navigation", "nav", "menu", "sidebar", "footer", "header", "breadcrumb"]',
        'id_=["navigation", "nav", "menu", "sidebar", "footer", "header"]'
    ]:
        # 安全のため個別に処理
        pass
    
    # よくあるクラス名で削除
    common_remove_classes = ['navigation', 'nav', 'menu', 'sidebar', 'footer', 'header', 'breadcrumb', 'ad', 'advertisement']
    for class_name in common_remove_classes:
        for element in soup.find_all(class_=lambda x: x and class_name in x.lower()):
            element.decompose()
    
    # テキスト抽出
    text = soup.get_text(separator='\n', strip=True)
    
    # テキスト正規化
    text = normalize_text(text)
    
    # 長さチェック
    if len(text) < min_length:
        return None
    
    return text


def normalize_text(text: str) -> str:
    """
    テキストを正規化
    
    Args:
        text: 正規化対象のテキスト
    
    Returns:
        正規化されたテキスト
    """
    # 連続する空白を1つに
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 連続する改行を最大2つに
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 行頭・行末の空白を削除
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # 全体のトリム
    text = text.strip()
    
    return text


def extract_headings(html: str) -> list:
    """
    HTMLから見出し構造を抽出
    
    Args:
        html: HTML文字列
    
    Returns:
        見出しのリスト（各要素は {level: int, text: str} の辞書）
    """
    soup = BeautifulSoup(html, 'lxml')
    headings = []
    
    for level in range(1, 7):  # h1〜h6
        for heading in soup.find_all(f'h{level}'):
            text = heading.get_text(strip=True)
            if text:
                headings.append({
                    'level': level,
                    'text': text
                })
    
    return headings


def split_by_headings(html: str) -> list:
    """
    HTMLを見出しごとにセクション分割
    
    Args:
        html: HTML文字列
    
    Returns:
        セクションのリスト（各要素は {heading: str, level: int, content: str} の辞書）
    """
    soup = BeautifulSoup(html, 'lxml')
    sections = []
    current_section = {'heading': '', 'level': 0, 'content': []}
    
    for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'ul', 'ol']):
        if element.name.startswith('h'):
            # 新しいセクション開始
            if current_section['content']:
                # 前のセクションを保存
                current_section['content'] = '\n'.join(current_section['content'])
                sections.append(current_section.copy())
            
            # 新しいセクション開始
            level = int(element.name[1])
            heading_text = element.get_text(strip=True)
            current_section = {
                'heading': heading_text,
                'level': level,
                'content': []
            }
        else:
            # コンテンツを追加
            text = element.get_text(strip=True)
            if text:
                current_section['content'].append(text)
    
    # 最後のセクション
    if current_section['content']:
        current_section['content'] = '\n'.join(current_section['content'])
        sections.append(current_section)
    
    return sections

