(() => {
  const IGNORE_TAGS = new Set([
    'SCRIPT', 'STYLE', 'NOSCRIPT', 'IFRAME', 'SVG', 'NAV', 'FOOTER', 'HEADER',
  ]);

  function extractText(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent.trim();
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    if (IGNORE_TAGS.has(node.tagName)) return '';
    if (node.getAttribute('aria-hidden') === 'true') return '';
    if (node.offsetHeight === 0 && node.offsetWidth === 0) return '';

    const parts = [];
    for (const child of node.childNodes) {
      const t = extractText(child);
      if (t) parts.push(t);
    }
    return parts.join('\n');
  }

  const article = document.querySelector('article') || document.querySelector('main') || document.body;
  let text = extractText(article);

  // 연속 빈 줄 정리 + 최대 3000자
  text = text.replace(/\n{3,}/g, '\n\n').trim().slice(0, 3000);
  return text;
})();
