/**
 * Lightweight Markdown renderer for assistant messages.
 */

import { useMemo } from 'react';
function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function inline(text) {
  let out = escapeHtml(text);
  out = out.replace(/`([^`]+)`/g, (_, c) => `<code>${c}</code>`);
  out = out.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/__([^_]+?)__/g, '<strong>$1</strong>');
  out = out.replace(/(^|[^*])\*([^*\n]+?)\*(?!\*)/g, '$1<em>$2</em>');
  out = out.replace(/(^|[^_])_([^_\n]+?)_(?!_)/g, '$1<em>$2</em>');
  out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  return out;
}
function toHtml(src) {
  const text = (src || '').replace(/\r\n/g, '\n').replace(/(?<!\d) \* (?!\d)/g, '\n* ');
  const lines = text.split('\n');
  const html = [];
  let list = null;
  let para = [];
  let code = null;
  const flushPara = () => {
    if (para.length) {
      html.push(`<p>${para.map(inline).join('<br/>')}</p>`);
      para = [];
    }
  };
  const flushList = () => {
    if (list) {
      const items = list.items.map(it => `<li>${inline(it)}</li>`).join('');
      html.push(`<${list.type}>${items}</${list.type}>`);
      list = null;
    }
  };
  for (const line of lines) {
    if (/^\s*```/.test(line)) {
      if (code) {
        html.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`);
        code = null;
      } else {
        flushPara();
        flushList();
        code = [];
      }
      continue;
    }
    if (code) {
      code.push(line);
      continue;
    }
    const trimmed = line.trim();
    if (!trimmed) {
      flushPara();
      flushList();
      continue;
    }
    const h = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      flushPara();
      flushList();
      const lvl = h[1].length;
      html.push(`<h${lvl}>${inline(h[2])}</h${lvl}>`);
      continue;
    }
    const ul = trimmed.match(/^[*\-+]\s+(.*)$/);
    if (ul) {
      flushPara();
      if (!list || list.type !== 'ul') {
        flushList();
        list = {
          type: 'ul',
          items: []
        };
      }
      list.items.push(ul[1]);
      continue;
    }
    const ol = trimmed.match(/^(\d+)[.)]\s+(.*)$/);
    if (ol) {
      flushPara();
      if (!list || list.type !== 'ol') {
        flushList();
        list = {
          type: 'ol',
          items: []
        };
      }
      list.items.push(ol[2]);
      continue;
    }
    flushList();
    para.push(trimmed);
  }
  flushPara();
  flushList();
  if (code) html.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`);
  return html.join('');
}
export default function Markdown({
  text,
  className
}) {
  const html = useMemo(() => toHtml(text), [text]);
  return <div className={className ? `markdown ${className}` : 'markdown'} dangerouslySetInnerHTML={{
    __html: html
  }} />;
}
