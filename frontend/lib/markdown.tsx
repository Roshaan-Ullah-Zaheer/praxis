import type { ReactNode } from "react";

/**
 * Minimal answer renderer: supports **bold**, `-`/`*` bullet lists, paragraphs,
 * and inline `[n]` citation markers (handed off to a render callback so they can
 * become interactive chips). Deliberately tiny — model answers are short and we
 * don't want a full markdown dependency in the bundle.
 */

const TOKEN = /(\*\*[^*]+\*\*)|(\[\d+\])/g;

function renderInline(text: string, renderCite?: (n: number) => ReactNode): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let key = 0;
  let match: RegExpExecArray | null;
  TOKEN.lastIndex = 0;
  while ((match = TOKEN.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const tok = match[0];
    if (tok.startsWith("**")) {
      nodes.push(<strong key={key++}>{tok.slice(2, -2)}</strong>);
    } else {
      const n = Number(tok.slice(1, -1));
      nodes.push(renderCite ? <span key={key++}>{renderCite(n)}</span> : tok);
    }
    last = match.index + tok.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function RichText({
  text,
  renderCite,
}: {
  text: string;
  renderCite?: (n: number) => ReactNode;
}) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let bullets: string[] = [];
  let key = 0;

  const flush = () => {
    if (bullets.length) {
      blocks.push(
        <ul key={`u${key++}`}>
          {bullets.map((b, i) => (
            <li key={i}>{renderInline(b, renderCite)}</li>
          ))}
        </ul>,
      );
      bullets = [];
    }
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (/^[-*]\s+/.test(trimmed)) {
      bullets.push(trimmed.replace(/^[-*]\s+/, ""));
    } else {
      flush();
      if (trimmed) blocks.push(<p key={`p${key++}`}>{renderInline(trimmed, renderCite)}</p>);
    }
  }
  flush();

  return <div className="answer-body text-[14px] leading-relaxed text-ink">{blocks}</div>;
}
