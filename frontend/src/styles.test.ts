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
      expect(wide).toMatch(new RegExp(`\\.${table}\\s+thead\\s+th:nth-child\\(\\d\\)\\s*{[^}]*width:`));
    }
    expect(wide).toMatch(/\.doc-name\s*{[^}]*text-overflow:\s*ellipsis[^}]*white-space:\s*nowrap/);
  });

  it("o texto corrido das tabelas é justificado com hifenização e não quebra uma letra por linha", () => {
    expect(css).toMatch(/\.text-block\s*{[^}]*text-align:\s*justify[^}]*hyphens:\s*auto/);
    expect(css).toMatch(/\.wide-table\s+td\s*{[^}]*overflow-wrap:\s*break-word/);
  });

  it("FORA-02: a faixa do documento fora do interstício tem a cor de alerta e fica presa ao cartão em telas estreitas", () => {
    expect(css).toMatch(
      /\.doc-outside-banner\s+td\s*{[^}]*background:\s*#fff4e5[^}]*border-left:\s*4px solid var\(--alerta\)[^}]*color:\s*var\(--alerta\)/,
    );
    const narrow = block("@media (max-width: 959px)");
    expect(narrow).toMatch(/tr\.doc-outside\s*{[^}]*margin-bottom:\s*0/);
    expect(narrow).toMatch(/\.doc-outside-banner\s+td::before\s*{[^}]*content:\s*none/);
  });

  it("abaixo de 960 px as tabelas largas viram cartões com o rótulo de cada coluna", () => {
    const narrow = block("@media (max-width: 959px)");
    expect(narrow).toMatch(/\.wide-table\s+thead\s*{[^}]*display:\s*none/);
    expect(narrow).toMatch(/\.wide-table\s+td\s*[,{][^}]*display:\s*block/);
    expect(narrow).toMatch(/content:\s*attr\(data-label\)/);
  });
});


describe("UIG-07: a Etapa 5 cabe em 360 px sem rolagem horizontal da página", () => {
  const STEP_CLASSES = [
    "generated-block",
    "generation-history",
    "generation-alerts",
    "report-editor",
    "report-section",
    "report-entries",
    "report-entry-",
    "layout-editor",
    "layout-group",
    "layout-item",
    "layout-activities",
    "layout-activity-head",
    "layout-pages",
    "disclosure",
    "dossier-list",
  ];
  const rules = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .map((m) => ({ selector: m[1].replace(/@media[^{]*$/, "").trim(), body: m[2] }))
    .filter((r) => STEP_CLASSES.some((c) => r.selector.includes(`.${c}`)));

  it("há regras para os blocos, o editor do Relatório, o arranjo e a ordem do dossiê", () => {
    for (const c of STEP_CLASSES) {
      expect(
        rules.some((r) => r.selector.includes(`.${c}`)),
        c,
      ).toBe(true);
    }
  });

  it("nenhuma regra da etapa impõe largura mínima ou fixa acima de 360 px", () => {
    const wide = rules.flatMap((r) =>
      [...r.body.matchAll(/(?:^|[\s;])(width|min-width|flex-basis)\s*:\s*([\d.]+)(px|rem|em)/g)]
        .map((m) => ({ selector: r.selector, prop: m[1], px: toPx(m[2], m[3]) }))
        .filter((d) => d.px > 360),
    );
    expect(wide).toEqual([]);
  });

  it("nenhuma regra da etapa força rolagem horizontal, tabela ou linha sem quebra", () => {
    for (const r of rules) {
      expect(r.body, r.selector).not.toMatch(/overflow(-x)?\s*:\s*(auto|scroll)/);
      expect(r.body, r.selector).not.toMatch(/white-space\s*:\s*nowrap/);
      expect(r.body, r.selector).not.toMatch(/display\s*:\s*(table|inline-table)|table-layout/);
    }
  });

  it("as linhas de página, de rodapé de entrada e de histórico quebram em vez de estourar a largura", () => {
    for (const selector of [".layout-pages > li", ".report-entry-foot", ".generation-history li", ".layout-activity-head"]) {
      const rule = rules.find((r) => r.selector === selector);
      expect(rule, selector).toBeDefined();
      expect(rule!.body, selector).toMatch(/flex-wrap\s*:\s*wrap/);
    }
  });

  it("os campos de texto do rascunho e do arranjo ocupam a largura do cartão e não passam dela", () => {
    const rule = rules.find((r) => r.selector.includes(".report-editor textarea"));
    expect(rule).toBeDefined();
    expect(rule!.body).toMatch(/width\s*:\s*100%/);
    expect(rule!.body).toMatch(/max-width\s*:\s*100%/);
  });

  it("abaixo de 480 px as páginas do arranjo viram uma lista empilhada, com os botões na largura toda", () => {
    const narrow = [...css.matchAll(/@media\s*\(max-width:\s*480px\)\s*{([\s\S]*?)\n}\n/g)].map((m) => m[1]).join("\n");
    expect(narrow).toMatch(/\.layout-pages\s*>\s*li\s*{[^}]*flex-direction:\s*column/);
    expect(narrow).toMatch(/\.layout-pages\s+\.row-actions\s*[,{][^}]*width:\s*100%/);
  });

  it("a etapa usa listas e cartões, nunca tabelas (as tabelas viram listas)", async () => {
    const sources = import.meta.glob(
      [
        "./components/GeneratedBlock.tsx",
        "./components/ReportDraftEditor.tsx",
        "./components/ComprovanteLayoutEditor.tsx",
        "./components/DossierOrder.tsx",
        "./components/ConcludeDialog.tsx",
        "./pages/ProcessGenerated.tsx",
      ],
      { query: "?raw", import: "default", eager: true },
    ) as Record<string, string>;
    expect(Object.keys(sources)).toHaveLength(6);
    for (const [file, text] of Object.entries(sources)) {
      expect(text, file).not.toMatch(/<table/);
    }
  });
});
