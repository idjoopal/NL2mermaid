"""
Web Search Module

외부 검색 API(Perplexity, Tavily)를 활용한 웹 검색 모듈입니다.
"""
from src.modules.web_search.service import web_search_service

__all__ = ["web_search_service"]
