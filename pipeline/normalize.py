"""Módulo de normalización y deduplicación de contenido en Radar30X.

Limpia URLs de tracking/UTMs, normaliza títulos y elimina ítems redundantes
entre múltiples fuentes antes del procesamiento temático.
"""

import logging
from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from rapidfuzz import fuzz

from sources.base import RawItem

logger = logging.getLogger(__name__)

# Parámetros que no aportan valor canónico a la URL
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "source",
}


def canonicalize_url(url: str) -> str:
    """Elimina parámetros de rastreo (UTM, etc.) y normaliza la URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        netloc = parsed.netloc.lower()
        # Eliminar tracking params
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        clean_pairs = [(k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS]
        clean_query = urlencode(clean_pairs)
        clean_path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
        return urlunparse((parsed.scheme.lower(), netloc, clean_path, parsed.params, clean_query, ""))
    except Exception:
        return url.strip()


def normalize_and_deduplicate(items: List[RawItem], title_similarity_threshold: float = 90.0) -> List[RawItem]:
    """Deduplica ítems por URL canónica y similitud textual de título.

    Args:
        items: Lista de RawItems provenientes de diferentes ingestores.
        title_similarity_threshold: Porcentaje mínimo para considerar títulos idénticos.

    Returns:
        Lista de RawItems únicos normalizados.
    """
    seen_urls = set()
    unique_items: List[RawItem] = []

    for item in items:
        # 1. Normalizar URL
        clean_url = canonicalize_url(item.url)
        item.url = clean_url

        if clean_url in seen_urls:
            continue

        # 2. Verificar similitud con títulos ya admitidos
        title_norm = item.titulo.strip().lower()
        is_duplicate = False
        for accepted in unique_items:
            sim = fuzz.ratio(title_norm, accepted.titulo.strip().lower())
            if sim >= title_similarity_threshold:
                is_duplicate = True
                # Agregar métricas de la nueva mención al ítem existente
                accepted.metricas["menciones_duplicadas"] = (
                    accepted.metricas.get("menciones_duplicadas", 1) + 1
                )
                break

        if not is_duplicate:
            seen_urls.add(clean_url)
            unique_items.append(item)

    logger.info(
        "Normalización completada: de %d ítems originales a %d ítems únicos.",
        len(items),
        len(unique_items),
    )
    return unique_items
