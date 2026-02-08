"""
Web Scraper Utility for Auto-Archivist
Extracts title and main content from URLs using BeautifulSoup.
"""
import logging

import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict

logger = logging.getLogger(__name__)

async def extract_content_from_url(url: str) -> Dict[str, str]:
    """
    Extracts title, content, and description from a given URL.
    
    Args:
        url (str): Target URL
        
    Returns:
        dict: {
            "title": str,
            "content": str,
            "description": str,
            "image": str (optional)
        }
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract Metadata
            title = soup.title.string if soup.title else ""
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"]
                
            description = ""
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                description = og_desc["content"]
            
            image = ""
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                image = og_image["content"]

            # Extract Main Content (Simple Heuristic: P tags)
            # Improvement: Use 'trafilatura' or 'readability-lxml' for better extraction in future
            paragraphs = soup.find_all('p')
            content_text = "\n\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
            
            if not content_text:
                content_text = description  # Fallback
                
            return {
                "title": title.strip(),
                "content": content_text[:10000],  # Limit size
                "description": description.strip(),
                "image": image
            }
            
    except Exception as e:
        logger.exception("Scraper error for URL: %s", url)
        return {
            "title": "Failed to load",
            "content": f"Error loading URL: {str(e)}",
            "description": "",
            "image": ""
        }
