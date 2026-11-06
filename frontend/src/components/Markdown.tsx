import React from 'react';

// Hiển thị Markdown cơ bản; mọi nội dung render thành phần tử React, không dùng dangerouslySetInnerHTML.

const INLINE = /(\*\*[^*]+\*\*|\[[^\]]+\]\([^)\s]+\)|`[^`]+`)/g;

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  return text.split(INLINE).filter(Boolean).map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={key}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={key} className="px-1 py-0.5 rounded bg-stone-100 text-[0.9em]">{part.slice(1, -1)}</code>;
    }
    const link = part.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/);
    if (link && /^https?:\/\//.test(link[2])) {
      return (
        <a key={key} href={link[2]} target="_blank" rel="noreferrer" className="text-amber-800 underline underline-offset-2 hover:text-amber-950">
          {link[1]}
        </a>
      );
    }
    return <React.Fragment key={key}>{part}</React.Fragment>;
  });
}

const splitRow = (line: string) => line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());

export const Markdown: React.FC<{ text: string }> = ({ text }) => {
  const lines = text.split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    const key = `b-${i}`;

    if (!trimmed) { i++; continue; }

    // Bảng: dòng tiêu đề | ... | + dòng phân cách |---|
    if (trimmed.startsWith('|') && /^\|?\s*:?-{3,}/.test(lines[i + 1]?.trim() ?? '')) {
      const header = splitRow(trimmed);
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(splitRow(lines[i++]));
      blocks.push(
        <div key={key} className="overflow-x-auto border border-stone-200 rounded-lg">
          <table className="w-full text-[11px] border-collapse">
            <thead className="bg-stone-50">
              <tr>{header.map((h, j) => <th key={j} className="p-2 text-left font-semibold text-stone-700 border-b border-stone-200">{renderInline(h, `${key}-h${j}`)}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {rows.map((r, ri) => (
                <tr key={ri}>{r.map((c, j) => <td key={j} className="p-2 align-top text-stone-800">{renderInline(c, `${key}-${ri}-${j}`)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      const size = heading[1].length <= 2 ? 'text-base' : 'text-sm';
      blocks.push(<h4 key={key} className={`${size} font-bold text-stone-900 pt-1`}>{renderInline(heading[2], key)}</h4>);
      i++;
      continue;
    }

    if (trimmed.startsWith('>')) {
      const quote: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) quote.push(lines[i++].trim().replace(/^>\s?/, ''));
      blocks.push(
        <blockquote key={key} className="border-l-2 border-amber-400 bg-amber-50/60 px-3 py-2 rounded-r text-stone-700">
          {renderInline(quote.join(' '), key)}
        </blockquote>
      );
      continue;
    }

    const listItem = /^(\s*)([-*•]|\d+[.)])\s+(.*)$/;
    if (listItem.test(line)) {
      const ordered = /^\s*\d/.test(line);
      const items: { text: string; nested: boolean }[] = [];
      while (i < lines.length && listItem.test(lines[i])) {
        const m = lines[i].match(listItem)!;
        items.push({ text: m[3], nested: m[1].length >= 2 });
        i++;
      }
      const ListTag = ordered ? 'ol' : 'ul';
      blocks.push(
        <ListTag key={key} className={`${ordered ? 'list-decimal' : 'list-disc'} pl-5 space-y-1`}>
          {items.map((it, j) => <li key={j} className={it.nested ? 'ml-4' : ''}>{renderInline(it.text, `${key}-${j}`)}</li>)}
        </ListTag>
      );
      continue;
    }

    if (/^(-{3,}|\*{3,})$/.test(trimmed)) {
      blocks.push(<hr key={key} className="border-stone-200" />);
      i++;
      continue;
    }

    // Đoạn văn: gom các dòng liên tiếp
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|>|\||\s*([-*•]|\d+[.)])\s)/.test(lines[i].trim())) para.push(lines[i++].trim());
    if (!para.length) para.push(lines[i++].trim());
    blocks.push(<p key={key}>{renderInline(para.join(' '), key)}</p>);
  }

  return <div className="space-y-2">{blocks}</div>;
};
