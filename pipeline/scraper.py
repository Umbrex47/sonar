"""Módulo de Scraping Híbrido y Seguro para Sonar.

Implementa una arquitectura en cascada de costo $0 marginal con fallback anti-bloqueo:
1. Capa 0 (Costo $0): Jina Reader (https://r.jina.ai/) — Extracción directa de artículos en Markdown limpio optimizado para LLMs.
2. Capa 1 (Costo $0): Direct Stealth (httpx + BeautifulSoup) — Fingerprints de navegadores modernos, bypass de headers, extracción semántica de <article>/<main>, sin dependencias de terceros.
3. Capa 2 (Fallback Managed): ZenRows / ScraperAPI / ScrapingBee — Activado solo ante bloqueos severos (403, 429, Cloudflare Turnstile/CAPTCHA) para conservar créditos.

Incluye protección contra SSRF, rate limiting con jitter adaptativo por dominio y sanitización de texto.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import html
import ipaddress
import json
import logging
import os
import random
import re
import socket
import threading
import time
from typing import Any, Dict, List, Optional
import urllib.parse

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import feedparser
import httpx

load_dotenv()
logger = logging.getLogger(__name__)

# Pool de User-Agents reales de navegadores modernos (Desktop & Mobile)
MODERN_USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.4.1 Safari/605.1.15"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
]

BLOCKED_INDICATORS = [
    "attention required! | cloudflare",
    "just a moment...",
    "cloudflare ray id",
    "access denied",
    "security check to continue",
    "please turn javascript on and reload the page",
    "cf-browser-verification",
    "ddos-guard",
    "shield_recaptcha",
    "waf_challenge",
]


@dataclass
class ScrapeResult:
    """Resultado estructurado de extracción web."""
    url: str
    status: str  # "success" | "blocked" | "error"
    title: str
    content_markdown: str
    content_text: str
    method_used: str  # "jina_reader" | "direct_stealth" | "zenrows" | "scraperapi" | "scrapingbee"
    cost_estimate: str  # "$0.00" o costo del proveedor
    domain: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    latency_ms: float = 0.0
    tokens_estimate: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    """Resultado individual de búsqueda web multi-motor."""
    url: str
    title: str
    snippet: str
    engine: str  # "google_news" | "duckduckgo_direct" | "zenrows_duckduckgo" | "bing"
    published_date: Optional[str] = None
    author: Optional[str] = None
    enriched: bool = False
    content_markdown: Optional[str] = None
    tokens_estimate: int = 0
    cost_estimate: str = "$0.00"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HybridScraper:
    """Extractor híbrido de contenido web con cascada de fallback y protección de seguridad."""

    def __init__(
        self,
        zenrows_api_key: Optional[str] = None,
        scraperapi_key: Optional[str] = None,
        scrapingbee_key: Optional[str] = None,
        enable_jitter: bool = True,
    ):
        self.zenrows_api_key = zenrows_api_key or os.getenv("ZENROWS_API_KEY", "").strip()
        self.scraperapi_key = scraperapi_key or os.getenv("SCRAPER_API_KEY", "").strip()
        self.scrapingbee_key = scrapingbee_key or os.getenv("SCRAPINGBEE_API_KEY", "").strip()
        self.enable_jitter = enable_jitter

        self._domain_last_request: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado de disponibilidad de los motores de scraping."""
        return {
            "motores": {
                "jina_reader": {
                    "disponible": True,
                    "costo": "$0.00",
                    "descripcion": "Extracción RAG en Markdown vía r.jina.ai",
                },
                "direct_stealth": {
                    "disponible": True,
                    "costo": "$0.00",
                    "descripcion": "Peticiones locales httpx con rotación de User-Agents y limpieza BeautifulSoup",
                },
                "zenrows": {
                    "disponible": bool(self.zenrows_api_key),
                    "costo": "Pay-per-success (~$0.001 - $0.003)",
                    "descripcion": "Bypass managed de Cloudflare Turnstile y CAPTCHA",
                },
                "scraperapi": {
                    "disponible": bool(self.scraperapi_key),
                    "costo": "Pay-per-success (~$0.001)",
                    "descripcion": "Rotación residencial con reintentos automáticos",
                },
                "scrapingbee": {
                    "disponible": bool(self.scrapingbee_key),
                    "costo": "Pay-per-success (~$0.002)",
                    "descripcion": "Renderizado headless JS en la nube",
                },
            },
            "seguridad": {
                "ssrf_protection": True,
                "jitter_politeness": self.enable_jitter,
                "user_agents_count": len(MODERN_USER_AGENTS),
            },
        }

    def validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Valida que la URL sea segura y previene ataques SSRF hacia redes locales."""
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False, "Esquema no permitido (solo http/https)."

            hostname = parsed.hostname
            if not hostname:
                return False, "Host inválido en la URL."

            # Bloqueo de dominios locales estándar
            if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "local"):
                return False, "Acceso a loopback / localhost denegado por seguridad SSRF."

            # Resolver IP y comprobar si es privada/reservada
            try:
                ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                    return False, f"La IP {ip_str} pertenece a una red privada o restringida."
            except Exception:
                # Si falla resolución DNS, la petición fallará naturalmente en el fetch
                pass

            return True, None
        except Exception as e:
            return False, f"Error al validar URL: {e}"

    @staticmethod
    def resolve_google_news_url(url: str, timeout: float = 6.0) -> Optional[str]:
        """Resuelve URLs agregadas de Google News (news.google.com/rss/articles/...) al enlace original."""
        try:
            parsed = urllib.parse.urlparse(url)
            if "news.google.com" not in (parsed.hostname or ""):
                return None
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 2 or path_parts[-2] not in ("articles", "read"):
                return None

            art_id = path_parts[-1]
            params_url = f"https://news.google.com/rss/articles/{art_id}?hl=es-419&gl=CO&ceid=CO:es-419"

            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(params_url)
                if resp.status_code != 200:
                    return None

                html_text = resp.text
                sg_m = re.search(r'data-n-a-sg="([^"]+)"', html_text)
                ts_m = re.search(r'data-n-a-ts="([^"]+)"', html_text)
                if not sg_m or not ts_m:
                    return None

                sig, ts = sg_m.group(1), ts_m.group(1)
                ctx = [
                    ["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
                    "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0,
                ]
                inner = ["garturlreq", ctx, art_id, int(ts) if ts.isdigit() else ts, sig]
                envelopes = [["Fbv4je", json.dumps(inner, separators=(",", ":")), None, "0"]]
                body = f"f.req={urllib.parse.quote(json.dumps([envelopes], separators=(',', ':')))}"

                post_resp = client.post(
                    "https://news.google.com/_/DotsSplashUi/data/batchexecute",
                    headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
                    content=body,
                )
                if post_resp.status_code != 200:
                    return None

                text = post_resp.text
                if "\n\n" in text:
                    text = text.split("\n\n", 1)[1]
                text = text.lstrip()
                if text.startswith(")]}'"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[4:]
                    text = text.lstrip()

                rows = json.loads(text)
                for row in rows:
                    if isinstance(row, list) and len(row) >= 3 and row[1] == "Fbv4je":
                        payload = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                        if isinstance(payload, list) and payload and payload[0] == "garturlres":
                            canonical = payload[1]
                            if canonical and canonical.startswith(("http://", "https://")):
                                return canonical
        except Exception as e:
            logger.debug("No se pudo decodificar URL de Google News %s: %s", url, e)
        return None

    def _apply_domain_jitter(self, domain: str, min_delay: float = 0.5, max_delay: float = 1.8) -> None:
        """Aplica un retraso aleatorio entre peticiones consecutivas al mismo dominio."""
        if not self.enable_jitter:
            return

        with self._lock:
            now = time.time()
            last = self._domain_last_request.get(domain, 0.0)
            elapsed = now - last
            required_wait = random.uniform(min_delay, max_delay)

            if elapsed < required_wait:
                sleep_time = required_wait - elapsed
                time.sleep(sleep_time)

            self._domain_last_request[domain] = time.time()

    def _get_stealth_headers(self) -> Dict[str, str]:
        """Genera un set de cabeceras HTTP que emula a un navegador real moderno."""
        ua = random.choice(MODERN_USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Linux"',
        }

    def _is_blocked(self, status_code: int, body_text: str) -> bool:
        """Determina si la respuesta indica bloqueo anti-bot o Cloudflare challenge."""
        if status_code in (403, 429, 503):
            return True

        lower_body = (body_text or "").lower()
        if any(indicator in lower_body for indicator in BLOCKED_INDICATORS):
            return True

        return False

    def scrape_jina(self, url: str, timeout: float = 18.0) -> Optional[ScrapeResult]:
        """Extrae contenido mediante el servicio gratuito Jina Reader (Costo $0)."""
        start_time = time.time()
        jina_url = f"https://r.jina.ai/{url}"
        parsed_domain = urllib.parse.urlparse(url).netloc.replace("www.", "")

        headers = {
            "User-Agent": "SonarEditorialBot/1.0 (+https://perte.design/sonar)",
            "Accept": "text/plain",
            "X-Return-Format": "markdown",
        }

        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(jina_url, headers=headers)

                if resp.status_code == 200:
                    text_content = resp.text.strip()
                    if len(text_content) > 100 and not self._is_blocked(resp.status_code, text_content):
                        # Extraer título si viene en formato Markdown '# Titulo' o 'Title: ...'
                        title = parsed_domain
                        title_match = re.search(r"^Title:\s*(.+)$", text_content, re.MULTILINE)
                        if title_match:
                            title = title_match.group(1).strip()
                        else:
                            h1_match = re.search(r"^#\s+(.+)$", text_content, re.MULTILINE)
                            if h1_match:
                                title = h1_match.group(1).strip()

                        # Extraer autor si existe
                        author = None
                        author_match = re.search(r"^Author:\s*(.+)$", text_content, re.MULTILINE)
                        if author_match:
                            author = author_match.group(1).strip()

                        # Extraer fecha si existe
                        pub_date = None
                        date_match = re.search(r"^Published Date:\s*(.+)$", text_content, re.MULTILINE)
                        if date_match:
                            pub_date = date_match.group(1).strip()

                        latency = round((time.time() - start_time) * 1000, 1)
                        tokens_est = max(1, len(text_content.split()))

                        return ScrapeResult(
                            url=url,
                            status="success",
                            title=title,
                            content_markdown=text_content,
                            content_text=re.sub(r"[#*`_\-\[\]\(\)]", " ", text_content),
                            method_used="jina_reader",
                            cost_estimate="$0.00",
                            domain=parsed_domain,
                            author=author,
                            published_date=pub_date,
                            latency_ms=latency,
                            tokens_estimate=tokens_est,
                        )
                logger.info("Jina Reader devolvió status %d para %s", resp.status_code, url)
        except Exception as e:
            logger.warning("Fallo al consultar Jina Reader para %s: %s", url, e)

        return None

    def scrape_stealth(self, url: str, timeout: float = 15.0) -> Optional[ScrapeResult]:
        """Extrae contenido directamente con httpx y BeautifulSoup emulando un navegador real."""
        start_time = time.time()
        parsed_domain = urllib.parse.urlparse(url).netloc.replace("www.", "")

        headers = self._get_stealth_headers()

        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
                resp = client.get(url)

                if self._is_blocked(resp.status_code, resp.text):
                    logger.info("Bloqueo detectado en direct stealth para %s (Status: %d)", url, resp.status_code)
                    return None

                if resp.status_code != 200:
                    logger.warning("Status %d al consultar %s en direct stealth", resp.status_code, url)
                    return None

                return self._parse_html_to_result(
                    html_text=resp.text,
                    url=url,
                    method_used="direct_stealth",
                    cost_estimate="$0.00",
                    start_time=start_time,
                )
        except Exception as e:
            logger.warning("Fallo en direct stealth para %s: %s", url, e)

        return None

    def _parse_html_to_result(
        self,
        html_text: str,
        url: str,
        method_used: str,
        cost_estimate: str,
        start_time: float,
    ) -> Optional[ScrapeResult]:
        """Convierte HTML arbitrario en un ScrapeResult limpio y estructurado en Markdown."""
        parsed_domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
        soup = BeautifulSoup(html_text, "html.parser")

        # 1. Extraer metadatos OpenGraph / Twitter Cards
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        if not title:
            title = parsed_domain

        author = None
        author_meta = (
            soup.find("meta", attrs={"name": "author"})
            or soup.find("meta", property="article:author")
        )
        if author_meta and author_meta.get("content"):
            author = author_meta["content"].strip()

        published_date = None
        date_meta = (
            soup.find("meta", property="article:published_time")
            or soup.find("meta", attrs={"name": "publish-date"})
        )
        if date_meta and date_meta.get("content"):
            published_date = date_meta["content"].strip()

        # 2. Eliminar elementos basura / no contenido
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "svg", "noscript"]):
            tag.decompose()

        # 3. Localizar contenedor semántico prioritario
        content_container = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_=re.compile(r"content|post-body|article-body|entry-content", re.I))
            or soup.find("body")
        )

        if not content_container:
            return None

        # 4. Convertir encabezados y párrafos a Markdown limpio
        markdown_lines = []
        if title:
            markdown_lines.append(f"# {title}\n")
        if author:
            markdown_lines.append(f"*Autor: {author}*")
        if published_date:
            markdown_lines.append(f"*Publicado: {published_date}*")
        if author or published_date:
            markdown_lines.append("\n---\n")

        for elem in content_container.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "blockquote", "pre"]):
            name = elem.name
            txt = elem.get_text(separator=" ", strip=True)
            if not txt or len(txt) < 3:
                continue

            if name == "h1":
                markdown_lines.append(f"\n# {txt}\n")
            elif name == "h2":
                markdown_lines.append(f"\n## {txt}\n")
            elif name == "h3":
                markdown_lines.append(f"\n### {txt}\n")
            elif name == "h4":
                markdown_lines.append(f"\n#### {txt}\n")
            elif name == "blockquote":
                markdown_lines.append(f"> {txt}\n")
            elif name == "pre":
                markdown_lines.append(f"```\n{txt}\n```\n")
            elif name in ("ul", "ol"):
                for li in elem.find_all("li"):
                    li_txt = li.get_text(strip=True)
                    if li_txt:
                        markdown_lines.append(f"- {li_txt}")
            else:  # p
                markdown_lines.append(f"{txt}\n")

        full_markdown = "\n".join(markdown_lines).strip()
        if len(full_markdown) < 60:
            full_markdown = content_container.get_text(separator="\n", strip=True)

        latency = round((time.time() - start_time) * 1000, 1)
        tokens_est = max(1, len(full_markdown.split()))

        return ScrapeResult(
            url=url,
            status="success",
            title=title,
            content_markdown=full_markdown,
            content_text=content_container.get_text(separator=" ", strip=True),
            method_used=method_used,
            cost_estimate=cost_estimate,
            domain=parsed_domain,
            author=author,
            published_date=published_date,
            latency_ms=latency,
            tokens_estimate=tokens_est,
        )

    def scrape_zenrows(self, url: str, timeout: float = 25.0) -> Optional[ScrapeResult]:
        """Capa 2 de Fallback: Extrae a través de ZenRows API (Bypass de Cloudflare/Turnstile)."""
        if not self.zenrows_api_key:
            return None

        start_time = time.time()
        zenrows_endpoint = "https://api.zenrows.com/v1/"
        params = {
            "apikey": self.zenrows_api_key,
            "url": url,
            "js_render": "true",
            "premium_proxy": "true",
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(zenrows_endpoint, params=params)
                if resp.status_code == 200:
                    return self._parse_html_to_result(
                        html_text=resp.text,
                        url=url,
                        method_used="zenrows",
                        cost_estimate="~$0.002",
                        start_time=start_time,
                    )
                logger.warning("ZenRows devolvió código %d", resp.status_code)
        except Exception as e:
            logger.warning("Fallo en ZenRows para %s: %s", url, e)

        return None

    def scrape_scraperapi(self, url: str, timeout: float = 25.0) -> Optional[ScrapeResult]:
        """Capa 2 alternativa de Fallback: Extrae a través de ScraperAPI (Rotación residencial)."""
        if not self.scraperapi_key:
            return None

        start_time = time.time()
        params = {
            "api_key": self.scraperapi_key,
            "url": url,
            "render": "true",
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get("https://api.scraperapi.com/", params=params)
                if resp.status_code == 200:
                    return self._parse_html_to_result(
                        html_text=resp.text,
                        url=url,
                        method_used="scraperapi",
                        cost_estimate="~$0.001",
                        start_time=start_time,
                    )
        except Exception as e:
            logger.warning("Fallo en ScraperAPI para %s: %s", url, e)

        return None

    def scrape(
        self,
        url: str,
        mode: str = "auto",
        timeout: float = 18.0,
    ) -> ScrapeResult:
        """Punto de entrada principal del scraper híbrido.
        
        Args:
            url: URL del sitio a extraer.
            mode: 'auto' (cascada completa), 'jina', 'stealth', o 'managed'.
            timeout: Tiempo límite en segundos.
        
        Returns:
            ScrapeResult estructurado.
        """
        # 1. Validación de seguridad SSRF
        is_safe, error_msg = self.validate_url(url)
        if not is_safe:
            return ScrapeResult(
                url=url,
                status="error",
                title="Error de Seguridad",
                content_markdown="",
                content_text="",
                method_used="security_validator",
                cost_estimate="$0.00",
                domain="invalid",
                error_message=error_msg,
            )

        # Si es un enlace de agregador Google News, resolver a la URL canónica de la fuente
        if "news.google.com" in url:
            resolved_url = self.resolve_google_news_url(url)
            if resolved_url:
                is_resolved_safe, _ = self.validate_url(resolved_url)
                if is_resolved_safe:
                    logger.info("URL de Google News resuelta a origen canónico: %s", resolved_url)
                    url = resolved_url

        parsed_domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
        self._apply_domain_jitter(parsed_domain)

        # Modo forzado individual si se solicita
        if mode == "jina":
            res = self.scrape_jina(url, timeout=timeout)
            if res:
                return res
        elif mode == "stealth":
            res = self.scrape_stealth(url, timeout=timeout)
            if res:
                return res
        elif mode == "managed":
            res = self.scrape_zenrows(url, timeout=timeout) or self.scrape_scraperapi(url, timeout=timeout)
            if res:
                return res

        # Cascada Automática Óptima (Auto)
        # Paso 1: Jina Reader (Costo $0, ultra-rápido, formato Markdown de alta fidelidad)
        res_jina = self.scrape_jina(url, timeout=timeout)
        if res_jina and len(res_jina.content_markdown) > 80:
            return res_jina

        # Paso 2: Direct Stealth con BeautifulSoup (Costo $0, navegador real emulado)
        res_stealth = self.scrape_stealth(url, timeout=timeout)
        if res_stealth and len(res_stealth.content_markdown) > 80:
            return res_stealth

        # Paso 3: Fallback a Servicios Managed si fueron configurados
        if self.zenrows_api_key:
            res_zen = self.scrape_zenrows(url, timeout=timeout + 10.0)
            if res_zen:
                return res_zen

        if self.scraperapi_key:
            res_sapi = self.scrape_scraperapi(url, timeout=timeout + 10.0)
            if res_sapi:
                return res_sapi

        # Si todo falló, retornar resultado con diagnóstico de bloqueo
        return ScrapeResult(
            url=url,
            status="blocked",
            title=f"Bloqueo o Error en {parsed_domain}",
            content_markdown="",
            content_text="",
            method_used="none",
            cost_estimate="$0.00",
            domain=parsed_domain,
            error_message=(
                "El sitio bloqueó el acceso directo (Cloudflare/CAPTCHA). "
                "Para desbloquear sitios protegidos, configure ZENROWS_API_KEY o SCRAPER_API_KEY en su archivo .env."
            ),
        )

    def search_web(
        self,
        query: str,
        limit: int = 15,
        enrich_top_k: int = 2,
        timeout: float = 12.0,
    ) -> List[SearchResult]:
        """Ejecuta una búsqueda web multi-motor optimizada para maximizar alcance de fuentes.
        
        Cascada:
        1. Capa 0 (Costo $0): Google News RSS Search con decodificación de enlaces canónicos.
        2. Capa 0 / Capa 1: DuckDuckGo HTML Search (direct stealth -> ZenRows proxy fallback).
        3. Capa 0 (Costo $0): Bing Search (stealth).
        4. Opcional: Enriquecimiento profundo con Jina Reader ($0.00) para los mejores 'enrich_top_k' enlaces.
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        results: List[SearchResult] = []
        seen_urls = set()

        # 1. Capa 0: Google News RSS Search (Noticias recientes, alta autoridad)
        try:
            encoded_q = urllib.parse.quote(clean_q)
            gnews_url = (
                f"https://news.google.com/rss/search?q={encoded_q}&hl=es-419&gl=MX&ceid=MX:es-419"
            )
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(
                    gnews_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.content)
                    for entry in feed.entries[:limit]:
                        title = getattr(entry, "title", "").strip()
                        link = getattr(entry, "link", "").strip()
                        summary = getattr(entry, "summary", "").strip()
                        published = getattr(entry, "published", "")
                        source_info = getattr(entry, "source", {})
                        author = (
                            source_info.get("title")
                            if isinstance(source_info, dict)
                            else "Google News"
                        )
                        clean_snip = re.sub(r"<[^>]+>", " ", summary)
                        clean_snip = html.unescape(clean_snip).strip()

                        if link and title and link not in seen_urls:
                            seen_urls.add(link)
                            results.append(
                                SearchResult(
                                    url=link,
                                    title=title,
                                    snippet=clean_snip[:400],
                                    engine="google_news",
                                    published_date=published,
                                    author=author,
                                )
                            )
        except Exception as e:
            logger.debug("Error en Google News search para '%s': %s", clean_q, e)

        # 2. Capa 0 / Capa 1: DuckDuckGo Search (Direct Stealth -> ZenRows Fallback)
        ddg_results: List[SearchResult] = []
        # Intento A: Direct Stealth
        try:
            headers = self._get_stealth_headers()
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                ddg_resp = client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": clean_q, "b": ""},
                    headers=headers,
                )
                if ddg_resp.status_code == 200 and "result__a" in ddg_resp.text:
                    soup = BeautifulSoup(ddg_resp.text, "html.parser")
                    for a in soup.find_all("a", class_="result__a")[:limit]:
                        raw_href = a.get("href", "")
                        final_url = raw_href
                        if "uddg=" in raw_href:
                            m = re.search(r"uddg=([^&]+)", raw_href)
                            if m:
                                final_url = urllib.parse.unquote(m.group(1))
                        t = a.get_text(strip=True)
                        if final_url and t and final_url not in seen_urls:
                            seen_urls.add(final_url)
                            ddg_results.append(
                                SearchResult(
                                    url=final_url,
                                    title=t,
                                    snippet="",
                                    engine="duckduckgo_direct",
                                )
                            )
        except Exception as e:
            logger.debug("Fallo directo en DDG para '%s': %s", clean_q, e)

        # Intento B: Si DDG directo falló o fue bloqueado, fallback a ZenRows si está configurado
        if not ddg_results and self.zenrows_api_key:
            try:
                target_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(clean_q)}"
                params = {
                    "apikey": self.zenrows_api_key,
                    "url": target_url,
                    "premium_proxy": "true",
                }
                zr_resp = httpx.get("https://api.zenrows.com/v1/", params=params, timeout=timeout + 5.0)
                if zr_resp.status_code == 200:
                    soup = BeautifulSoup(zr_resp.text, "html.parser")
                    for a in soup.find_all("a", class_="result__a")[:limit]:
                        raw_href = a.get("href", "")
                        final_url = raw_href
                        if "uddg=" in raw_href:
                            m = re.search(r"uddg=([^&]+)", raw_href)
                            if m:
                                final_url = urllib.parse.unquote(m.group(1))
                        t = a.get_text(strip=True)
                        if final_url and t and final_url not in seen_urls:
                            seen_urls.add(final_url)
                            ddg_results.append(
                                SearchResult(
                                    url=final_url,
                                    title=t,
                                    snippet="",
                                    engine="zenrows_duckduckgo",
                                )
                            )
            except Exception as e:
                logger.debug("Error en ZenRows DDG search para '%s': %s", clean_q, e)

        results.extend(ddg_results)

        # 3. Capa 0: Bing Search (stealth) si aún hay cupo
        if len(results) < limit:
            try:
                bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(clean_q)}"
                headers = self._get_stealth_headers()
                with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
                    b_resp = client.get(bing_url)
                    if b_resp.status_code == 200 and not b_resp.text.strip().startswith("<?xml"):
                        soup = BeautifulSoup(b_resp.text, "html.parser")
                        for li in soup.find_all("li", class_="b_algo")[:limit]:
                            h2 = li.find("h2")
                            if not h2:
                                continue
                            a = h2.find("a")
                            if not a or not a.get("href"):
                                continue
                            t = a.get_text(strip=True)
                            href = a["href"]
                            p = li.find("p")
                            snip = p.get_text(separator=" ", strip=True) if p else ""
                            if href and t and href not in seen_urls:
                                seen_urls.add(href)
                                results.append(
                                    SearchResult(
                                        url=href,
                                        title=t,
                                        snippet=snip[:350],
                                        engine="bing",
                                    )
                                )
            except Exception as e:
                logger.debug("Error en Bing search para '%s': %s", clean_q, e)

        # Limitar al total deseado
        truncated_results = results[:limit]

        # 4. Enriquecimiento profundo opcional para los mejores resultados
        if enrich_top_k > 0:
            for item in truncated_results[:enrich_top_k]:
                target_url = item.url
                if "news.google.com" in target_url:
                    resolved = self.resolve_google_news_url(target_url, timeout=5.0)
                    if resolved:
                        target_url = resolved
                        item.url = resolved

                try:
                    scrape_res = self.scrape(target_url, mode="auto", timeout=10.0)
                    if scrape_res.status == "success" and (scrape_res.content_markdown or scrape_res.content_text):
                        item.enriched = True
                        item.content_markdown = scrape_res.content_markdown
                        item.tokens_estimate = scrape_res.tokens_estimate
                        item.cost_estimate = scrape_res.cost_estimate
                        if scrape_res.content_markdown:
                            item.snippet = scrape_res.content_markdown[:380].strip()
                        if scrape_res.title and len(scrape_res.title) > 5:
                            item.title = scrape_res.title
                except Exception as e:
                    logger.debug("No se pudo enriquecer %s: %s", target_url, e)

        return truncated_results

