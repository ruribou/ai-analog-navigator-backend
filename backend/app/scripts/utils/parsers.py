"""
ページ種別ごとのHTMLパーサ
"""
from typing import Dict, Any
from bs4 import BeautifulSoup
import re

from .clean_text import clean_html_text, split_by_headings


def parse_department_top(html: str, url: str) -> Dict[str, Any]:
    """
    学系トップページのパース
    
    Args:
        html: HTML文字列
        url: ソースURL
    
    Returns:
        パース結果の辞書
    """
    soup = BeautifulSoup(html, 'lxml')
    
    # タイトル取得
    title_elem = soup.find('title')
    title = title_elem.get_text(strip=True) if title_elem else "情報システムデザイン学系"
    
    # 本文テキスト抽出
    text = clean_html_text(html)
    
    # セクション分割
    sections = split_by_headings(html)
    
    return {
        'url': url,
        'title': title,
        'text': text,
        'sections': sections,
        'metadata': {
            'campus': 'hatoyama',
            'department': '理工学部',
            'tags': ['department_overview', 'school_info']
        }
    }


def parse_faculty_list(html: str, url: str) -> Dict[str, Any]:
    """
    教員一覧ページのパース
    
    Args:
        html: HTML文字列
        url: ソースURL
    
    Returns:
        パース結果の辞書
    """
    soup = BeautifulSoup(html, 'lxml')
    
    # タイトル取得
    title_elem = soup.find('title')
    title = title_elem.get_text(strip=True) if title_elem else "教員一覧"
    
    # 本文テキスト抽出
    text = clean_html_text(html)
    
    # セクション分割
    sections = split_by_headings(html)
    
    return {
        'url': url,
        'title': title,
        'text': text,
        'sections': sections,
        'metadata': {
            'campus': 'hatoyama',
            'department': '理工学部',
            'tags': ['faculty_list', 'lab_list', 'school_info']
        }
    }


def parse_professor_detail(html: str, url: str) -> Dict[str, Any]:
    """
    教員詳細ページのパース（ra-data.dendai.ac.jp）
    
    Args:
        html: HTML文字列
        url: ソースURL
    
    Returns:
        パース結果の辞書
    """
    soup = BeautifulSoup(html, 'lxml')
    
    # タイトル・教員名を取得
    title_elem = soup.find('title')
    title = title_elem.get_text(strip=True) if title_elem else "教員情報"
    
    # 教員名を抽出（ページ構造に依存）
    professor_name = None
    h1_elem = soup.find('h1')
    if h1_elem:
        professor_name = h1_elem.get_text(strip=True)
    
    # 本文テキスト抽出
    text = clean_html_text(html)
    
    # セクション分割
    sections = split_by_headings(html)
    
    # 研究キーワード・専門分野の抽出（可能なら）
    keywords = []
    research_fields = []
    
    # テーブルから情報を抽出
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                header = cells[0].get_text(strip=True)
                content = cells[1].get_text(strip=True)
                
                if 'キーワード' in header or 'keyword' in header.lower():
                    keywords = [k.strip() for k in re.split(r'[,、]', content) if k.strip()]
                elif '専門' in header or '分野' in header:
                    research_fields = [f.strip() for f in re.split(r'[,、]', content) if f.strip()]
    
    metadata = {
        'campus': 'hatoyama',
        'department': '理工学部',
        'tags': ['faculty_profile', 'research_topic']
    }
    
    if professor_name:
        metadata['professor'] = [professor_name]
    
    if keywords:
        metadata['research_keywords'] = keywords
    
    if research_fields:
        metadata['research_fields'] = research_fields
    
    return {
        'url': url,
        'title': title,
        'text': text,
        'sections': sections,
        'metadata': metadata
    }


def parse_lab_about(html: str, url: str) -> Dict[str, Any]:
    """
    研究室ページのパース
    
    Args:
        html: HTML文字列
        url: ソースURL
    
    Returns:
        パース結果の辞書
    """
    soup = BeautifulSoup(html, 'lxml')
    
    # タイトル取得
    title_elem = soup.find('title')
    title = title_elem.get_text(strip=True) if title_elem else "研究室紹介"
    
    # 研究室名を抽出
    lab_name = None
    h1_elem = soup.find('h1')
    if h1_elem:
        lab_name = h1_elem.get_text(strip=True)
    
    # 本文テキスト抽出
    text = clean_html_text(html)
    
    # セクション分割
    sections = split_by_headings(html)
    
    # 指導教員の抽出（可能なら）
    professor = []
    # "神戸研" なら "神戸 英利" を追加
    if 'kamlab' in url.lower():
        professor = ['神戸 英利']
        lab_name = lab_name or '神戸研究室'
    
    metadata = {
        'campus': 'hatoyama',
        'department': '理工学部',
        'tags': ['lab', 'research_theme']
    }
    
    if lab_name:
        metadata['lab'] = lab_name
    
    if professor:
        metadata['professor'] = professor
    
    return {
        'url': url,
        'title': title,
        'text': text,
        'sections': sections,
        'metadata': metadata
    }


def parse_page(html: str, url: str) -> Dict[str, Any]:
    """
    URLに応じて適切なパーサを呼び出す
    
    Args:
        html: HTML文字列
        url: ソースURL
    
    Returns:
        パース結果の辞書
    """
    # URLパターンマッチング
    if 'rikougaku/rd/' in url and url.endswith('rd/'):
        return parse_department_top(html, url)
    elif 'kyoin.html' in url:
        return parse_faculty_list(html, url)
    elif 'ra-data.dendai.ac.jp' in url:
        return parse_professor_detail(html, url)
    elif 'kamlab.rd.dendai.ac.jp' in url:
        return parse_lab_about(html, url)
    else:
        # デフォルトパーサ（基本的な抽出のみ）
        return {
            'url': url,
            'title': 'Unknown Page',
            'text': clean_html_text(html),
            'sections': split_by_headings(html),
            'metadata': {
                'campus': 'hatoyama',
                'department': '理工学部',
                'tags': ['general']
            }
        }

