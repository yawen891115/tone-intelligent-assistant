import DOMPurify from 'dompurify';
import { marked } from 'marked';

export function renderAnswer(markdown: string, sourceCount: number): string {
    const html = marked.parse(markdown, { breaks: true, gfm: true }) as string;
    const container = document.createElement('div');
    container.append(DOMPurify.sanitize(html, { RETURN_DOM_FRAGMENT: true, USE_PROFILES: { html: true } }));

    container.querySelectorAll('a').forEach((link) => {
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
    });

    // Only replace citations in prose, preserving code, link labels and URL attributes.
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    const nodes: Text[] = [];
    while (walker.nextNode()) {
        const node = walker.currentNode as Text;
        if (!node.parentElement?.closest('pre, code, a, button') && node.data.includes('[')) nodes.push(node);
    }
    for (const node of nodes) {
        const fragment = document.createDocumentFragment();
        let offset = 0;
        for (const match of node.data.matchAll(/\[(\d{1,2})\]/g)) {
            const index = Number(match[1]);
            if (match.index === undefined || index < 1 || index > sourceCount) continue;
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'rag-cite';
            button.dataset.cite = String(index);
            button.setAttribute('aria-label', `查看来源 ${index}`);
            button.textContent = match[0];
            fragment.append(node.data.slice(offset, match.index), button);
            offset = match.index + match[0].length;
        }
        if (offset) {
            fragment.append(node.data.slice(offset));
            node.replaceWith(fragment);
        }
    }
    return container.innerHTML;
}
