import { describe, expect, it } from "vitest";
import css from "./styles.css?raw";
import html from "../index.html?raw";

const PX_PER_REM = 16;

function toPx(value: string, unit: string): number {
  const n = Number(value);
  return unit === "px" ? n : n * PX_PER_REM;
}

describe("UI-06: utilizável em 360 px sem rolagem horizontal", () => {
  it("não declara largura fixa ou mínima acima de 360 px", () => {
    const fixed = [
      ...css.matchAll(/(?:^|[\s;{])(width|min-width|flex-basis)\s*:\s*([\d.]+)(px|rem|em)/g),
    ].map((m) => ({ prop: m[1], px: toPx(m[2], m[3]) }));
    const gridMins = [...css.matchAll(/minmax\(\s*([\d.]+)(px|rem|em)/g)].map((m) => ({
      prop: "minmax",
      px: toPx(m[1], m[2]),
    }));
    const tooWide = [...fixed, ...gridMins].filter((d) => d.px > 360);
    expect(tooWide).toEqual([]);
  });

  it("usa contêineres fluidos e a meta viewport de dispositivo", () => {
    expect(css).toMatch(/\.container\s*{[^}]*width:\s*100%/);
    expect(html).toContain('name="viewport" content="width=device-width, initial-scale=1.0"');
  });

  it("TELA-08: abaixo de 480 px a tabela de pontuação vira cartões empilhados", () => {
    const media = css.match(/@media\s*\(max-width:\s*480px\)\s*{([\s\S]*?)\n}\n/);
    expect(media).not.toBeNull();
    expect(media![1]).toMatch(/\.scoring-table\s+td\s*[,{][^}]*display:\s*block/);
    expect(media![1]).toMatch(/\.scoring-table\s+thead\s*{[^}]*display:\s*none/);
    expect(media![1]).toMatch(/content:\s*attr\(data-label\)/);
  });
});

describe("UIM-01 / UIM-02 / UIM-10 / UIM-19: tabelas legíveis e botões", () => {
  const block = (query: string) => {
    const start = css.indexOf(query);
    expect(start).toBeGreaterThan(-1);
    let depth = 0;
    for (let i = css.indexOf("{", start); i < css.length; i++) {
      if (css[i] === "{") depth++;
      if (css[i] === "}" && --depth === 0) return css.slice(css.indexOf("{", start) + 1, i);
    }
    throw new Error("unbalanced css");
  };

  it("há botões primário, secundário e perigo, com estado desabilitado", () => {
    expect(css).toMatch(/\.btn-primary\s*{[^}]*background:/);
    expect(css).toMatch(/\.btn-secondary\s*{[^}]*background:[^}]*border:/);
    expect(css).toMatch(/\.btn-danger\s*{[^}]*background:\s*var\(--erro\)/);
    expect(css).toMatch(/\.btn:disabled\s*{[^}]*opacity/);
  });

  it("a partir de 960 px as colunas das tabelas têm larguras curtas e o nome trunca com reticências", () => {
    const wide = block("@media (min-width: 960px)");
    for (const table of ["doc-table", "review-table", "score-table"]) {
      expect(wide).toMatch(new RegExp(`\\.${table}\\b[^{}]*{[^}]*table-layout:\\s*fixed`));
      expect(wide).toMatch(new RegExp(`\\.${table}\\s+th:nth-child\\(\\d\\)\\s*{[^}]*width:`));
    }
    expect(wide).toMatch(/\.doc-name\s*{[^}]*text-overflow:\s*ellipsis[^}]*white-space:\s*nowrap/);
  });

  it("o texto corrido das tabelas é justificado com hifenização e não quebra uma letra por linha", () => {
    expect(css).toMatch(/\.text-block\s*{[^}]*text-align:\s*justify[^}]*hyphens:\s*auto/);
    expect(css).toMatch(/\.wide-table\s+td\s*{[^}]*overflow-wrap:\s*break-word/);
  });

  it("abaixo de 960 px as tabelas largas viram cartões com o rótulo de cada coluna", () => {
    const narrow = block("@media (max-width: 959px)");
    expect(narrow).toMatch(/\.wide-table\s+thead\s*{[^}]*display:\s*none/);
    expect(narrow).toMatch(/\.wide-table\s+td\s*[,{][^}]*display:\s*block/);
    expect(narrow).toMatch(/content:\s*attr\(data-label\)/);
  });
});

