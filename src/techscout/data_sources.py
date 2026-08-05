"""
Módulo para buscar dados de fontes online
Suporta NewsAPI, RSS feeds e scraping básico
"""
import time

try:
    import feedparser
    import requests
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

from techscout.logger import logger


class NewsAPIClient:
    """Cliente para NewsAPI (https://newsapi.org/)"""
    
    def __init__(self, api_key: str | None = None):
        """
        Inicializa cliente NewsAPI
        
        Args:
            api_key: Chave da API (obtenha em https://newsapi.org/)
        """
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.logger = logger
    
    def search_articles(
        self,
        query: str,
        language: str = "pt",
        sort_by: str = "publishedAt",
        page_size: int = 20
    ) -> list[dict]:
        """
        Busca artigos por query
        
        Args:
            query: Termo de busca
            language: Idioma (pt, en, etc)
            sort_by: Ordenação (publishedAt, relevancy, popularity)
            page_size: Número de resultados (máx 100)
            
        Returns:
            Lista de artigos
        """
        if not HAS_DEPENDENCIES:
            self.logger.error(
                "Biblioteca 'requests' não instalada. Execute: pip install requests"
            )
            return []
        
        if not self.api_key:
            self.logger.warning("NewsAPI key não configurada - usando fonte alternativa")
            return []
        
        try:
            url = f"{self.base_url}/everything"
            params: dict[str, str | int] = {
                "q": query,
                "language": language,
                "sortBy": sort_by,
                "pageSize": min(page_size, 100),
                "apiKey": self.api_key,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            
            self.logger.info(f"Encontrados {len(articles)} artigos para query: {query}")
            return articles
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro ao buscar artigos da NewsAPI: {e}")
            return []
    
    def get_top_headlines(
        self,
        category: str = "technology",
        country: str = "br",
        page_size: int = 20
    ) -> list[dict]:
        """
        Busca principais notícias por categoria
        
        Args:
            category: Categoria (technology, business, etc)
            country: País (br, us, etc)
            page_size: Número de resultados
            
        Returns:
            Lista de artigos
        """
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/top-headlines"
            params: dict[str, str | int] = {
                "category": category,
                "country": country,
                "pageSize": min(page_size, 100),
                "apiKey": self.api_key,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            
            self.logger.info(f"Encontradas {len(articles)} principais notícias de {category}")
            return articles
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro ao buscar headlines: {e}")
            return []


class RSSFeedReader:
    """Leitor de feeds RSS"""
    
    def __init__(self):
        self.logger = logger
    
    def fetch_feed(self, url: str, max_items: int = 20) -> list[dict]:
        """
        Busca itens de um feed RSS
        
        Args:
            url: URL do feed RSS
            max_items: Número máximo de itens
            
        Returns:
            Lista de itens do feed
        """
        if not HAS_DEPENDENCIES:
            self.logger.error(
                "Biblioteca 'feedparser' não instalada. "
                "Execute: pip install feedparser"
            )
            return []
        
        try:
            feed = feedparser.parse(url)
            
            items = []
            for entry in feed.entries[:max_items]:
                items.append({
                    "title": entry.get("title", ""),
                    "description": entry.get("description", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "content": entry.get("summary", entry.get("description", ""))
                })
            
            self.logger.info(f"Carregados {len(items)} itens do feed: {url}")
            return items
            
        except Exception as e:
            self.logger.error(f"Erro ao ler feed RSS {url}: {e}")
            return []


class TechNewsCollector:
    """Coletor de notícias de tecnologia de múltiplas fontes"""
    
    # Feeds RSS populares de tecnologia
    RSS_FEEDS = [
        "https://rss.tecnoblog.net/feed/",
        "https://www.tecmundo.com.br/feed",
        "https://canaltech.com.br/feed/",
        "https://www.olhardigital.com.br/feed/",
    ]
    
    def __init__(self, newsapi_key: str | None = None):
        """
        Inicializa coletor
        
        Args:
            newsapi_key: Chave da NewsAPI (opcional)
        """
        self.newsapi = NewsAPIClient(newsapi_key) if newsapi_key else None
        self.rss_reader = RSSFeedReader()
        self.logger = logger
    
    def collect_from_rss(self, max_items_per_feed: int = 10) -> list[str]:
        """
        Coleta notícias de feeds RSS
        
        Args:
            max_items_per_feed: Máximo de itens por feed
            
        Returns:
            Lista de textos de notícias
        """
        all_texts = []
        
        for feed_url in self.RSS_FEEDS:
            try:
                items = self.rss_reader.fetch_feed(feed_url, max_items_per_feed)
                
                for item in items:
                    # Combina título e descrição
                    corpo = item.get("content", item.get("description", ""))
                    text = f"{item.get('title', '')}\n\n{corpo}"
                    if text.strip():
                        all_texts.append(text.strip())
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                self.logger.warning(f"Erro ao processar feed {feed_url}: {e}")
                continue
        
        self.logger.info(f"Coletados {len(all_texts)} textos de feeds RSS")
        return all_texts
    
    def collect_from_newsapi(
        self,
        queries: list[str] | None = None,
        max_articles: int = 20
    ) -> list[str]:
        """
        Coleta notícias da NewsAPI
        
        Args:
            queries: Lista de queries de busca
            max_articles: Número máximo de artigos
            
        Returns:
            Lista de textos de notícias
        """
        if not self.newsapi:
            return []
        
        if queries is None:
            queries = [
                "startup",
                "tecnologia",
                "inteligência artificial",
                "investimento",
                "venture capital"
            ]
        
        all_texts = []
        
        for query in queries:
            try:
                articles = self.newsapi.search_articles(
                    query=query,
                    language="pt",
                    page_size=max_articles // len(queries) + 1
                )
                
                for article in articles:
                    # Combina título, descrição e conteúdo
                    title = article.get("title", "")
                    description = article.get("description", "")
                    content = article.get("content", "")
                    
                    text = f"{title}\n\n{description}\n\n{content}"
                    if text.strip():
                        all_texts.append(text.strip())
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                self.logger.warning(f"Erro ao buscar query '{query}': {e}")
                continue
        
        self.logger.info(f"Coletados {len(all_texts)} textos da NewsAPI")
        return all_texts
    
    def collect_all(
        self,
        use_newsapi: bool = True,
        use_rss: bool = True,
        max_items: int = 50
    ) -> list[str]:
        """
        Coleta de todas as fontes disponíveis
        
        Args:
            use_newsapi: Usar NewsAPI
            use_rss: Usar feeds RSS
            max_items: Número máximo de itens
            
        Returns:
            Lista de textos coletados
        """
        all_texts = []
        
        if use_rss:
            self.logger.info("Coletando de feeds RSS...")
            rss_texts = self.collect_from_rss(max_items_per_feed=max_items // 4)
            all_texts.extend(rss_texts)
        
        if use_newsapi and self.newsapi:
            self.logger.info("Coletando da NewsAPI...")
            newsapi_texts = self.collect_from_newsapi(max_articles=max_items)
            all_texts.extend(newsapi_texts)
        
        # Remove duplicatas (por título)
        seen_titles = set()
        unique_texts = []
        for text in all_texts:
            title = text.split("\n")[0] if "\n" in text else text[:50]
            if title not in seen_titles:
                seen_titles.add(title)
                unique_texts.append(text)
        
        self.logger.info(f"Total de {len(unique_texts)} textos únicos coletados")
        return unique_texts[:max_items]


def format_article_text(article: dict) -> str:
    """
    Formata artigo em texto para ingestão
    
    Args:
        article: Dicionário com dados do artigo
        
    Returns:
        Texto formatado
    """
    parts = []
    
    if article.get("title"):
        parts.append(article["title"])
    
    if article.get("description"):
        parts.append(article["description"])
    
    if article.get("content"):
        # Remove tags HTML se houver
        content = article["content"]
        if "<" in content:
            import re
            content = re.sub(r'<[^>]+>', '', content)
        parts.append(content)
    
    return "\n\n".join(parts)

