"""Ingestor para Newsletters y Publicaciones Especializadas de IA y Ecosistema LatAm.

Fuentes públicas vía RSS:
- The Rundown AI (https://www.therundown.ai/feed)
- Startups LatAm (https://startupslatam.com/feed/)
- Rest of World (https://restofworld.org/feed/)
- TechCrunch AI (https://techcrunch.com/category/artificial-intelligence/feed/)

100% público, compliant, sin paywall ni scraping no autorizado.
Aporta señales tempranas de inversión, casos de uso empresarial y curaduría editorial de alto nivel.
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import List
import feedparser
import httpx

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class NewslettersSource(BaseSource):
    """Adaptador para boletines y publicaciones clave de IA y negocios."""

    name: str = "Newsletters"
    FEEDS = [
        ("The Rundown AI", "https://www.therundown.ai/feed"),
        ("Startups LatAm", "https://startupslatam.com/feed/"),
        ("Rest of World", "https://restofworld.org/feed/latest/"),
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("Latent Space", "https://www.latent.space/feed"),
        ("Interconnects", "https://www.interconnects.ai/feed"),
        ("Import AI", "https://importai.substack.com/feed"),
        ("Simon Willison", "https://simonwillison.net/atom/everything/"),
        ("OpenAI News", "https://openai.com/news/rss.xml"),
        ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
        ("ArXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI"),
        ("MIT Tech Review", "https://www.technologyreview.com/topic/artificial-intelligence/feed/"),
    ]

    def fetch(self, limit: int = 40) -> List[RawItem]:
        """Descarga y filtra artículos recientes con relevancia para la audiencia de 30X."""
        items: List[RawItem] = []
        import re
        import time

        ai_keywords = [
            "ai", "ia", "agent", "agente", "llm", "slm", "model", "rag", "automation",
            "automatiz", "startup", "founder", "operaciones", "banca", "fintech",
            "inversion", "venture", "latam", "software", "tecnologia", "deepseek",
            "openai", "anthropic", "meta", "llama", "prompt", "benchmark", "eval",
            "evals", "reasoning", "coding", "workflow", "inference", "gpu", "token",
            "leadership", "liderazgo", "ceo", "cto", "management", "cultura", "talento",
            "retencion", "scaleup", "saas", "cloud", "ciberseguridad", "devops", "arquitectura"
        ]

        inherently_ai_publications = {
            "The Rundown AI", "Latent Space", "Interconnects", "Import AI",
            "OpenAI News", "Hugging Face Blog", "ArXiv cs.AI", "TechCrunch AI", "MIT Tech Review"
        }

        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Radar30XBot/1.0"},
            ) as client:
                per_feed_limit = max(3, limit // len(self.FEEDS) + 2)
                for publication_name, feed_url in self.FEEDS:
                    try:
                        resp = client.get(feed_url)
                        if resp.status_code != 200:
                            logger.warning("Newsletter feed %s retornó status %d", publication_name, resp.status_code)
                            continue

                        feed = feedparser.parse(resp.content)
                        for entry in feed.entries[:per_feed_limit]:
                            title = getattr(entry, "title", "").strip()
                            if not title:
                                continue

                            # Obtener resumen o descripción y limpiar etiquetas HTML
                            raw_summary = (
                                getattr(entry, "summary", "")
                                or getattr(entry, "description", "")
                            )
                            if not raw_summary and hasattr(entry, "content") and entry.content:
                                raw_summary = entry.content[0].get("value", "")
                            clean_summary = re.sub(r"<[^>]+>", " ", str(raw_summary))
                            clean_summary = re.sub(r"\s+", " ", clean_summary).strip()

                            combined_text = f"{title} {clean_summary}".lower()

                            # Descartar ruido evidente no relacionado con tecnología / IA
                            noise_keywords = ["freight", "shipping fleet", "red sea", "ev shipping", "petroleo", "kindergarten", "gaza", "yemen"]
                            if any(nk in combined_text for nk in noise_keywords):
                                continue

                            # Filtrar solo piezas con relevancia si la fuente no es 100% IA
                            if publication_name not in inherently_ai_publications:
                                if not any(kw in combined_text for kw in ai_keywords):
                                    continue

                            # Filtro de recencia (últimos 10 días para captar análisis de fin de semana)
                            pub_parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
                            if pub_parsed:
                                pub_ts = time.mktime(pub_parsed)
                                if time.time() - pub_ts > (10 * 86400):
                                    continue

                            link = getattr(entry, "link", "").strip()
                            author = getattr(entry, "author", "") or publication_name
                            published = (
                                getattr(entry, "published", "")
                                or getattr(entry, "updated", "")
                                or datetime.now(timezone.utc).isoformat()
                            )

                            item_id = hashlib.sha256(f"nl:{publication_name}:{link or title}".encode()).hexdigest()[:16]

                            items.append(
                                RawItem(
                                    id=item_id,
                                    fuente=f"{publication_name}",
                                    titulo=title,
                                    resumen=clean_summary[:350].strip(),
                                    url=link or feed_url,
                                    autor=author,
                                    fecha=published,
                                    metricas={
                                        "formato": "articulo",
                                        "tipo_fuente": "newsletter_rss",
                                        "publicacion": publication_name,
                                        "relevancia": 1.3 if publication_name in inherently_ai_publications else 1.1,
                                    },
                                )
                            )
                    except Exception as sub_exc:
                        logger.warning("Error al procesar feed %s: %s", publication_name, sub_exc)
        except Exception as exc:
            logger.error("Error en NewslettersSource: %s", exc)

        logger.info("Newsletters: %d ítems recolectados desde %d feeds.", len(items), len(self.FEEDS))
        return items
