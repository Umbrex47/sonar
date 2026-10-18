"""Paquete de fuentes de datos para Radar30X.

Exporta adaptadores para Hacker News, YouTube, Google News, Medium, GitHub, Reddit y CSV Manual.
"""

from typing import List
from sources.base import BaseSource, RawItem
from sources.hackernews import HackerNewsSource
from sources.youtube import YouTubeSource
from sources.googlenews import GoogleNewsSource
from sources.medium import MediumSource
from sources.github import GitHubSource
from sources.reddit import RedditSource
from sources.manual import ManualCSVSource
from sources.huggingface import HuggingFaceSource
from sources.newsletters import NewslettersSource
from sources.rssapp import RSSAppSource
from sources.websearch import WebSearchSource

__all__ = [
    "BaseSource",
    "RawItem",
    "HackerNewsSource",
    "YouTubeSource",
    "GoogleNewsSource",
    "MediumSource",
    "GitHubSource",
    "RedditSource",
    "ManualCSVSource",
    "HuggingFaceSource",
    "NewslettersSource",
    "RSSAppSource",
    "WebSearchSource",
    "get_default_sources",
]


def get_default_sources(include_optional: bool = True) -> List[BaseSource]:
    """Retorna la lista ordenada de adaptadores de fuentes según el plan de ejecución."""
    sources: List[BaseSource] = [
        HackerNewsSource(),
        YouTubeSource(),
        GoogleNewsSource(),
        WebSearchSource(),
        NewslettersSource(),
        RSSAppSource(),
        HuggingFaceSource(),
        MediumSource(),
        GitHubSource(),
        ManualCSVSource(),
    ]
    if include_optional:
        sources.append(RedditSource())
    return sources

