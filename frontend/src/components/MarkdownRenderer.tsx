"use client";

import React from "react";
import { ExternalLink } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content) return null;

  // Dividir el texto en bloques (párrafos, tablas, títulos, listas)
  const lines = content.split("\n");
  const blocks: React.ReactNode[] = [];
  let currentTable: string[] = [];
  let currentList: string[] = [];
  let inCodeBlock = false;
  let codeBlockLines: string[] = [];

  const flushList = (key: number) => {
    if (currentList.length > 0) {
      blocks.push(
        <ul key={`list-${key}`} className="space-y-1 my-2 pl-4 list-disc text-xs sm:text-[13px] text-[#27251e]">
          {currentList.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {formatInlineText(item)}
            </li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  const flushTable = (key: number) => {
    if (currentTable.length >= 2) {
      const headerLine = currentTable[0];
      const dataLines = currentTable.slice(2); // saltar la línea separadora |---|---|

      const parseRow = (line: string) => {
        return line
          .split("|")
          .map((c) => c.trim())
          .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      };

      const headers = parseRow(headerLine);
      const rows = dataLines.map(parseRow);

      blocks.push(
        <div key={`table-wrapper-${key}`} className="overflow-x-auto my-3 border border-[#d1d1cd] rounded-[6px] shadow-xs">
          <table className="w-full text-left text-xs border-collapse bg-[#faf8f5]">
            <thead>
              <tr className="border-b border-[#d1d1cd] bg-[#fdfbfa]">
                {headers.map((h, hIdx) => (
                  <th
                    key={hIdx}
                    className="p-2.5 font-mono text-[10px] text-[#72706b] uppercase tracking-wider font-medium"
                  >
                    {formatInlineText(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, rIdx) => (
                <tr
                  key={rIdx}
                  className="border-b border-[#d1d1cd]/50 last:border-b-0 hover:bg-[#016a71]/5 transition"
                >
                  {r.map((cell, cIdx) => (
                    <td key={cIdx} className="p-2.5 text-[#27251e] leading-snug">
                      {formatInlineText(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      currentTable = [];
    }
  };

  const flushCodeBlock = (key: number) => {
    if (codeBlockLines.length > 0) {
      blocks.push(
        <pre
          key={`code-${key}`}
          className="p-3 my-2 rounded-[6px] bg-[#27251e] text-[#faf8f5] font-mono text-xs overflow-x-auto leading-relaxed"
        >
          {codeBlockLines.join("\n")}
        </pre>
      );
      codeBlockLines = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Manejo de bloques de código
    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        flushCodeBlock(i);
        inCodeBlock = false;
      } else {
        flushList(i);
        flushTable(i);
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    const trimmed = line.trim();

    // Líneas horizontales separadoras
    if (trimmed === "---" || trimmed === "***" || trimmed === "___") {
      flushList(i);
      flushTable(i);
      blocks.push(<hr key={`hr-${i}`} className="my-4 border-[#d1d1cd]" />);
      continue;
    }

    // Tablas Markdown (| col | col |)
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      flushList(i);
      currentTable.push(line);
      continue;
    } else if (currentTable.length > 0) {
      flushTable(i);
    }

    // Citas / Blockquotes (> texto)
    if (trimmed.startsWith("> ")) {
      flushList(i);
      blocks.push(
        <blockquote
          key={`quote-${i}`}
          className="border-l-3 border-[#016a71] pl-3 py-1.5 my-2.5 bg-[#fdfbfa] italic text-[#72706b] rounded-r text-xs sm:text-[13px] leading-relaxed"
        >
          {formatInlineText(trimmed.replace(/^>\s*/, ""))}
        </blockquote>
      );
      continue;
    }

    // Listas con viñetas (- item o * item)
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      currentList.push(trimmed.substring(2));
      continue;
    } else if (currentList.length > 0) {
      flushList(i);
    }

    // Encabezados (con o sin indentación)
    if (trimmed.startsWith("#### ")) {
      blocks.push(
        <h5 key={`h4-${i}`} className="text-xs sm:text-sm font-semibold text-[#27251e] mt-3 mb-1">
          {formatInlineText(trimmed.replace(/^####\s+/, ""))}
        </h5>
      );
      continue;
    }
    if (trimmed.startsWith("### ")) {
      blocks.push(
        <h4 key={`h3-${i}`} className="text-sm sm:text-base font-semibold text-[#016a71] mt-4 mb-2 flex items-center space-x-2">
          <span>{formatInlineText(trimmed.replace(/^###\s+/, ""))}</span>
        </h4>
      );
      continue;
    }
    if (trimmed.startsWith("## ")) {
      blocks.push(
        <h3 key={`h2-${i}`} className="text-base sm:text-lg font-semibold text-[#27251e] mt-5 mb-2 pb-1 border-b border-[#d1d1cd]/60">
          {formatInlineText(trimmed.replace(/^##\s+/, ""))}
        </h3>
      );
      continue;
    }
    if (trimmed.startsWith("# ")) {
      blocks.push(
        <h2 key={`h1-${i}`} className="text-lg sm:text-xl font-bold text-[#27251e] mt-6 mb-3 pb-1 border-b border-[#d1d1cd]">
          {formatInlineText(trimmed.replace(/^#\s+/, ""))}
        </h2>
      );
      continue;
    }

    // Líneas vacías
    if (trimmed === "") {
      continue;
    }

    // Párrafo normal
    blocks.push(
      <p key={`p-${i}`} className="my-2 text-xs sm:text-[13px] text-[#27251e] leading-relaxed">
        {formatInlineText(trimmed)}
      </p>
    );
  }

  // Flush final
  flushList(lines.length);
  flushTable(lines.length);
  flushCodeBlock(lines.length);

  return <div className="space-y-1">{blocks}</div>;
}

/** Formatea texto inline con negrita, código, cursiva y enlaces */
function formatInlineText(text: string): React.ReactNode {
  if (!text) return "";

  // Tokenizar por negrita (**...**) y código (`...`)
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  // Regex para capturar **negrita**, `codigo`, *cursiva*, [link](url)
  const regex = /(\*\*.*?\*\*|`.*?`|\*.*?\*|\[.*?\]\(.*?\))/g;
  let match;
  let lastIndex = 0;

  while ((match = regex.exec(text)) !== null) {
    // Texto previo al match
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const matchedStr = match[0];
    if (matchedStr.startsWith("**") && matchedStr.endsWith("**")) {
      parts.push(
        <strong key={`b-${keyIdx++}`} className="font-medium text-[#27251e]">
          {matchedStr.slice(2, -2)}
        </strong>
      );
    } else if (matchedStr.startsWith("`") && matchedStr.endsWith("`")) {
      parts.push(
        <code
          key={`c-${keyIdx++}`}
          className="font-mono text-[11px] px-1 py-0.2 rounded-[3px] bg-[#d1d1cd]/30 text-[#016a71] border border-[#d1d1cd]/50"
        >
          {matchedStr.slice(1, -1)}
        </code>
      );
    } else if (matchedStr.startsWith("*") && matchedStr.endsWith("*")) {
      parts.push(
        <em key={`i-${keyIdx++}`} className="italic text-[#72706b]">
          {matchedStr.slice(1, -1)}
        </em>
      );
    } else if (matchedStr.startsWith("[") && matchedStr.includes("](")) {
      const linkMatch = matchedStr.match(/\[(.*?)\]\((.*?)\)/);
      if (linkMatch) {
        parts.push(
          <a
            key={`a-${keyIdx++}`}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#016a71] hover:underline inline-flex items-center space-x-0.5"
          >
            <span>{linkMatch[1]}</span>
            <ExternalLink className="w-2.5 h-2.5 inline ml-0.5" />
          </a>
        );
      }
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}
