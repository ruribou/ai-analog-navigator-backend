"""
transcription_corrector のテスト
"""
import pytest
from app.services.transcription_corrector import normalize_with_domain_terms


class TestNormalizeWithDomainTerms:
    """辞書による正規化のテスト"""
    
    def test_kanbe_normalization(self):
        """神戸（かんべ）の誤変換パターンを正規化"""
        test_cases = [
            ("こうべ先生の研究室", "神戸先生の研究室"),
            ("かみどひでとし教授", "神戸ひでとし教授"),
            ("神部先生に質問したい", "神戸先生に質問したい"),
        ]
        
        domain_dict = {
            "こうべ": "神戸",
            "かみど": "神戸",
            "神部": "神戸",
        }
        
        for input_text, expected in test_cases:
            result = normalize_with_domain_terms(input_text, domain_dict)
            assert result == expected, f"Expected '{expected}', got '{result}'"
    
    def test_university_name_normalization(self):
        """大学名の略称を正式名称に正規化"""
        test_cases = [
            ("でんだいのオープンキャンパス", "東京電機大学のオープンキャンパス"),
            ("電大に行きたい", "東京電機大学に行きたい"),
            ("でんきだいの情報を教えて", "東京電機大学の情報を教えて"),
            ("東京電気大学の学部", "東京電機大学の学部"),
        ]
        
        domain_dict = {
            "でんだい": "東京電機大学",
            "電大": "東京電機大学",
            "でんきだい": "東京電機大学",
            "東京電気大学": "東京電機大学",
        }
        
        for input_text, expected in test_cases:
            result = normalize_with_domain_terms(input_text, domain_dict)
            assert result == expected, f"Expected '{expected}', got '{result}'"
    
    def test_technical_terms_normalization(self):
        """専門用語の正規化"""
        test_cases = [
            ("いいおーてぃーについて教えて", "IoTについて教えて"),
            ("アイオーティーの研究", "IoTの研究"),
            ("しーぴーえすとは", "CPSとは"),
        ]
        
        domain_dict = {
            "いいおーてぃー": "IoT",
            "アイオーティー": "IoT",
            "しーぴーえす": "CPS",
        }
        
        for input_text, expected in test_cases:
            result = normalize_with_domain_terms(input_text, domain_dict)
            assert result == expected, f"Expected '{expected}', got '{result}'"
    
    def test_multiple_replacements(self):
        """複数の置換を同時に実行"""
        input_text = "でんだいのこうべ先生がいいおーてぃーを研究しています"
        expected = "東京電機大学の神戸先生がIoTを研究しています"
        
        domain_dict = {
            "でんだい": "東京電機大学",
            "こうべ": "神戸",
            "いいおーてぃー": "IoT",
        }
        
        result = normalize_with_domain_terms(input_text, domain_dict)
        assert result == expected
    
    def test_no_replacements_when_not_found(self):
        """辞書に該当がない場合は変更しない"""
        input_text = "普通の文章です"
        expected = "普通の文章です"
        
        domain_dict = {
            "こうべ": "神戸",
        }
        
        result = normalize_with_domain_terms(input_text, domain_dict)
        assert result == expected
    
    def test_empty_dict(self):
        """空の辞書の場合は元のテキストを返す"""
        input_text = "こうべ先生の研究"
        expected = "こうべ先生の研究"
        
        result = normalize_with_domain_terms(input_text, {})
        assert result == expected
    
    def test_longer_pattern_priority(self):
        """長いパターンが優先されることを確認"""
        input_text = "かんべひでとし先生"
        expected = "神戸英利先生"
        
        # 長い順にソートされるので「かんべひでとし」が先に適用される
        domain_dict = {
            "かんべ": "神戸",
            "かんべひでとし": "神戸英利",
        }
        
        result = normalize_with_domain_terms(input_text, domain_dict)
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

