"""
Ingest Service - Content Extraction Pipeline
Based on Tech_Spec.md - Section 3.1

This is a deterministic (non-agent) service that:
1. Fetches URL content and extracts clean text
2. Generates embeddings (TODO: Phase 2)
3. Triggers Librarian agent for classification (TODO: Phase 2)
"""
import httpx
import re
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse


async def fetch_url_content(url: str) -> Tuple[str, str]:
    """
    Fetch URL and extract clean text content.
    Returns (title, content) tuple.
    
    Uses BeautifulSoup for basic HTML parsing.
    For production, consider using @mozilla/readability via Node subprocess.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = await client.get(url, headers=headers, follow_redirects=True)
        response.raise_for_status()
        html = response.text
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Extract title
    title = ""
    if soup.title:
        title = soup.title.string or ""
    
    # Try to find article content
    # Priority: article, main, body
    article = soup.find("article") or soup.find("main") or soup.find("body")
    
    if article:
        # Remove script, style, nav, footer, header, aside
        for tag in article.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
        
        # Get text and clean whitespace
        text = article.get_text(separator="\n", strip=True)
        
        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
    else:
        text = ""
    
    return title.strip(), text.strip()


def extract_domain(url: str) -> str:
    """Extract domain from URL for display"""
    parsed = urlparse(url)
    return parsed.netloc


async def process_web_content(url: str) -> dict:
    """
    Process a web URL and return structured data.
    
    Returns:
        {
            "title": str,
            "content": str,
            "source_url": str,
            "source_domain": str
        }
    """
    title, content = await fetch_url_content(url)
    
    # Fallback title from URL if not found
    if not title:
        title = f"Page from {extract_domain(url)}"
    
    return {
        "title": title,
        "content": content,
        "source_url": url,
        "source_domain": extract_domain(url)
    }


async def process_note_content(content: str, memo: Optional[str] = None) -> dict:
    """
    Process raw text/note content.
    
    Returns:
        {
            "title": str (first line or truncated),
            "content": str,
            "source_url": None
        }
    """
    # Generate title from first line or first 50 chars
    lines = content.strip().split("\n")
    first_line = lines[0] if lines else ""
    
    if len(first_line) > 50:
        title = first_line[:50] + "..."
    else:
        title = first_line or "Untitled Note"
    
    # Append memo if provided
    final_content = content
    if memo:
        final_content = f"{content}\n\n---\n**My thoughts:**\n{memo}"
    
    return {
        "title": title,
        "content": final_content,
        "source_url": None
    }
