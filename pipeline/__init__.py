"""Paquete del pipeline de procesamiento para Radar30X.

Incluye almacenamiento, deduplicación, agrupación temática, decisiones Jev,
scoring ponderado y redacción narrativa.
"""

from pipeline.db import Database
from pipeline.normalize import canonicalize_url, normalize_and_deduplicate
from pipeline.topics import TopicCluster, cluster_items, clean_topic_phrase
from pipeline.decide import ClusterDecision, decide_cluster
from pipeline.scoring import ScoredTopic, calculate_topic_score, rank_topics
from pipeline.narrative import generate_narrative

__all__ = [
    "Database",
    "canonicalize_url",
    "normalize_and_deduplicate",
    "TopicCluster",
    "cluster_items",
    "clean_topic_phrase",
    "ClusterDecision",
    "decide_cluster",
    "ScoredTopic",
    "calculate_topic_score",
    "rank_topics",
    "generate_narrative",
]
