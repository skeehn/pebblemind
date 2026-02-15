"""Real-time Web Data Integration for PebbleMind

Provides tools for accessing real-time web data including:
- Web search
- News feeds
- Weather data
- Stock prices
- RSS feeds
- Web scraping
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from lxml import etree

logger = logging.getLogger(__name__)

# Try to import feedparser, but it's optional (needs sgmllib which may not be available)
try:
    import feedparser
    HAS_FEEDPARSER = True
except (ImportError, ModuleNotFoundError):
    HAS_FEEDPARSER = False
    logger.warning("feedparser not available, using alternative RSS parsing")


class WebDataTools:
    """Tools for accessing real-time web data"""

    def __init__(self, cache_ttl: int = 300):
        """
        Initialize web data tools

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={'User-Agent': 'PebbleMind/1.0'}
        )
        return self

    async def __aexit__(self, *args):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if still valid"""
        if key in self._cache:
            cached = self._cache[key]
            if datetime.now() < cached['expires']:
                return cached['data']
        return None

    def _set_cache(self, key: str, data: Any):
        """Cache data with TTL"""
        self._cache[key] = {
            'data': data,
            'expires': datetime.now() + timedelta(seconds=self.cache_ttl)
        }

    def _parse_rss_with_lxml(self, xml_content: str, limit: int) -> List[Dict[str, str]]:
        """Parse RSS/Atom feed using lxml (fallback when feedparser unavailable)"""
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))
            entries = []

            # Try RSS 2.0 format
            items = root.findall('.//item')
            if not items:
                # Try Atom format
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')

            for item in items[:limit]:
                if item.tag == 'item':  # RSS
                    title = item.findtext('title', default='')
                    summary = item.findtext('description', default='')
                    link = item.findtext('link', default='')
                    published = item.findtext('pubDate', default='')
                    author = item.findtext('author', default='')
                else:  # Atom
                    title = item.findtext('{http://www.w3.org/2005/Atom}title', default='')
                    summary = item.findtext('{http://www.w3.org/2005/Atom}summary', default='')
                    link_elem = item.find('{http://www.w3.org/2005/Atom}link')
                    link = link_elem.get('href', '') if link_elem is not None else ''
                    published = item.findtext('{http://www.w3.org/2005/Atom}published', default='')
                    author_elem = item.find('{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name')
                    author = author_elem.text if author_elem is not None else ''

                entries.append({
                    'title': title.strip() if title else '',
                    'summary': summary.strip() if summary else '',
                    'link': link.strip() if link else '',
                    'published': published.strip() if published else '',
                    'author': author.strip() if author else ''
                })

            return entries
        except Exception as e:
            logger.error(f"RSS parsing with lxml failed: {e}")
            return []

    async def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search the web using DuckDuckGo (no API key required)

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of search results with title, snippet, url
        """
        cache_key = f"search:{query}:{num_results}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Use DuckDuckGo Instant Answer API
            url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    results = []

                    # Parse abstract
                    if data.get('Abstract'):
                        results.append({
                            'title': data.get('Heading', query),
                            'snippet': data['Abstract'],
                            'url': data.get('AbstractURL', '')
                        })

                    # Parse related topics
                    for topic in data.get('RelatedTopics', [])[:num_results]:
                        if isinstance(topic, dict) and 'Text' in topic:
                            results.append({
                                'title': topic.get('Text', '')[:100],
                                'snippet': topic.get('Text', ''),
                                'url': topic.get('FirstURL', '')
                            })

                    self._set_cache(cache_key, results)
                    return results[:num_results]

        except Exception as e:
            logger.error(f"Web search failed: {e}")

        return []

    async def get_news(self, topic: str = "technology", limit: int = 5) -> List[Dict[str, str]]:
        """
        Get latest news headlines

        Args:
            topic: News topic/category
            limit: Number of articles

        Returns:
            List of news articles with title, description, url, published_date
        """
        cache_key = f"news:{topic}:{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Use public RSS feeds (no API key required)
            feed_urls = {
                'technology': 'https://feeds.bbci.co.uk/news/technology/rss.xml',
                'world': 'https://feeds.bbci.co.uk/news/world/rss.xml',
                'business': 'https://feeds.bbci.co.uk/news/business/rss.xml',
                'science': 'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
            }

            feed_url = feed_urls.get(topic.lower(), feed_urls['technology'])

            async with self.session.get(feed_url) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    feed = feedparser.parse(xml_content)

                    articles = []
                    for entry in feed.entries[:limit]:
                        articles.append({
                            'title': entry.get('title', ''),
                            'description': entry.get('summary', ''),
                            'url': entry.get('link', ''),
                            'published_date': entry.get('published', '')
                        })

                    self._set_cache(cache_key, articles)
                    return articles

        except Exception as e:
            logger.error(f"News fetch failed: {e}")

        return []

    async def get_weather(self, location: str) -> Dict[str, Any]:
        """
        Get current weather for a location

        Args:
            location: City name or coordinates

        Returns:
            Weather data with temperature, conditions, etc.
        """
        cache_key = f"weather:{location}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Use wttr.in (no API key required)
            url = f"https://wttr.in/{quote_plus(location)}?format=j1"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    current = data.get('current_condition', [{}])[0]
                    weather = {
                        'location': location,
                        'temperature_c': current.get('temp_C', 'N/A'),
                        'temperature_f': current.get('temp_F', 'N/A'),
                        'feels_like_c': current.get('FeelsLikeC', 'N/A'),
                        'condition': current.get('weatherDesc', [{}])[0].get('value', 'N/A'),
                        'humidity': current.get('humidity', 'N/A'),
                        'wind_speed_kmph': current.get('windspeedKmph', 'N/A'),
                        'timestamp': datetime.now().isoformat()
                    }

                    self._set_cache(cache_key, weather)
                    return weather

        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")

        return {'error': 'Weather data unavailable'}

    async def scrape_url(self, url: str, extract: str = "text") -> Dict[str, Any]:
        """
        Scrape content from a URL

        Args:
            url: URL to scrape
            extract: What to extract ('text', 'title', 'links', 'all')

        Returns:
            Scraped content
        """
        cache_key = f"scrape:{url}:{extract}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()

                    result = {}

                    if extract in ['text', 'all']:
                        result['text'] = soup.get_text(separator=' ', strip=True)[:5000]

                    if extract in ['title', 'all']:
                        result['title'] = soup.title.string if soup.title else ''

                    if extract in ['links', 'all']:
                        result['links'] = [a.get('href') for a in soup.find_all('a', href=True)][:20]

                    result['url'] = url
                    result['timestamp'] = datetime.now().isoformat()

                    self._set_cache(cache_key, result)
                    return result

        except Exception as e:
            logger.error(f"URL scraping failed: {e}")

        return {'error': 'Scraping failed'}

    async def get_rss_feed(self, feed_url: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Parse RSS/Atom feed

        Args:
            feed_url: URL of RSS feed
            limit: Maximum number of entries

        Returns:
            List of feed entries
        """
        cache_key = f"rss:{feed_url}:{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            async with self.session.get(feed_url) as response:
                if response.status == 200:
                    xml_content = await response.text()

                    if HAS_FEEDPARSER:
                        # Use feedparser if available
                        feed = feedparser.parse(xml_content)
                        entries = []
                        for entry in feed.entries[:limit]:
                            entries.append({
                                'title': entry.get('title', ''),
                                'summary': entry.get('summary', ''),
                                'link': entry.get('link', ''),
                                'published': entry.get('published', ''),
                                'author': entry.get('author', '')
                            })
                    else:
                        # Use lxml as fallback
                        entries = self._parse_rss_with_lxml(xml_content, limit)

                    self._set_cache(cache_key, entries)
                    return entries

        except Exception as e:
            logger.error(f"RSS feed parsing failed: {e}")

        return []


# Tool definitions for LLM function calling
WEB_TOOLS = {
    "search_web": {
        "description": "Search the web for current information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results (1-10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    "get_news": {
        "description": "Get latest news headlines on a topic",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "News topic (technology, world, business, science)",
                    "default": "technology"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of articles (1-10)",
                    "default": 5
                }
            }
        }
    },
    "get_weather": {
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location"
                }
            },
            "required": ["location"]
        }
    },
    "scrape_url": {
        "description": "Extract content from a webpage",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to scrape"
                },
                "extract": {
                    "type": "string",
                    "description": "What to extract (text, title, links, all)",
                    "default": "text"
                }
            },
            "required": ["url"]
        }
    }
}


async def demo():
    """Demo real-time web data access"""
    async with WebDataTools(cache_ttl=300) as tools:
        print("="*60)
        print("REAL-TIME WEB DATA DEMO")
        print("="*60 + "\n")

        # Search
        print("🔍 Web Search: 'Python programming'")
        results = await tools.search_web("Python programming", num_results=3)
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['title']}")
            print(f"     {r['snippet'][:100]}...")
        print()

        # News
        print("📰 Latest Tech News:")
        news = await tools.get_news("technology", limit=3)
        for i, article in enumerate(news, 1):
            print(f"  {i}. {article['title']}")
        print()

        # Weather
        print("🌤️  Weather in London:")
        weather = await tools.get_weather("London")
        if 'temperature_c' in weather:
            print(f"  Temperature: {weather['temperature_c']}°C")
            print(f"  Condition: {weather['condition']}")
        print()


if __name__ == "__main__":
    asyncio.run(demo())
