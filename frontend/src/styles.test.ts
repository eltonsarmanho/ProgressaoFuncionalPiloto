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
        "./components/DossierChecklist.tsx",
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

describe("SEC-05: a região viva vazia do StepNav não ocupa espaço", () => {
  it("`.step-blocked:empty` zera a margem e a região não é escondida (continua no DOM, lida pelo leitor de tela)", () => {
    const empty = css.match(/\.step-blocked:empty\s*{([^}]*)}/);
    expect(empty).not.toBeNull();
    expect(empty![1]).toMatch(/margin:\s*0\s*;/);
    expect(empty![1]).not.toMatch(/display\s*:\s*none/);
    expect(empty![1]).not.toMatch(/visibility\s*:\s*hidden/);
    // With a message, the block keeps its own margin.
    expect(css).toMatch(/\.step-blocked\s*{[^}]*margin:\s*-0\.5rem 0 1rem/);
  });
});

describe("GRES-08: o painel da Etapa 4 cabe em 360 px sem rolagem horizontal da página", () => {
  const PANEL_CLASSES = [
    "scoring-panel",
    "panel-block",
    "panel-headline",
    "panel-value",
    "panel-scope",
    "panel-minimum",
    "group-bars",
    "group-bar",
    "group-bar-name",
    "group-bar-value",
    "group-bar-track",
    "group-bar-fill",
    "teaching",
    "teaching-period",
    "teaching-offers",
    "teaching-title",
    "teaching-level",
    "teaching-hours",
    "teaching-total",
    "potential-cards",
  ];
  const rules = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .map((m) => ({ selector: m[1].replace(/@media[^{]*$/, "").trim(), body: m[2] }))
    .filter((r) => PANEL_CLASSES.some((c) => new RegExp(`\\.${c}(?![\\w-])`).test(r.selector)));
  const rule = (selector: string) => {
    const found = rules.find((r) => r.selector === selector);
    expect(found, selector).toBeDefined();
    return found!.body;
  };

  it("há regras para cada classe do painel", () => {
    for (const c of PANEL_CLASSES) {
      expect(
        rules.some((r) => new RegExp(`\\.${c}(?![\\w-])`).test(r.selector)),
        c,
      ).toBe(true);
    }
  });

  it("nenhuma regra do painel impõe largura mínima ou fixa acima de 360 px", () => {
    const wide = rules.flatMap((r) =>
      [...r.body.matchAll(/(?:^|[\s;])(width|min-width|flex-basis)\s*:\s*([\d.]+)(px|rem|em)/g)]
        .map((m) => ({ selector: r.selector, prop: m[1], px: toPx(m[2], m[3]) }))
        .filter((d) => d.px > 360),
    );
    const gridMins = rules.flatMap((r) =>
      [...r.body.matchAll(/minmax\(\s*([\d.]+)(px|rem|em)/g)]
        .map((m) => ({ selector: r.selector, px: toPx(m[1], m[2]) }))
        .filter((d) => d.px > 360),
    );
    expect([...wide, ...gridMins]).toEqual([]);
  });

  it("nenhuma regra do painel força rolagem horizontal, tabela ou linha sem quebra", () => {
    for (const r of rules) {
      expect(r.body, r.selector).not.toMatch(/overflow(-x)?\s*:\s*(auto|scroll)/);
      expect(r.body, r.selector).not.toMatch(/white-space\s*:\s*nowrap/);
      expect(r.body, r.selector).not.toMatch(/display\s*:\s*(table|inline-table)|table-layout/);
    }
  });

  it("a linha da barra é uma grade 'minmax(0, 1fr) auto' e a barra ocupa a linha de baixo", () => {
    expect(rule(".group-bar")).toMatch(/display\s*:\s*grid/);
    expect(rule(".group-bar")).toMatch(/grid-template-columns\s*:\s*minmax\(0,\s*1fr\)\s+auto/);
    expect(rule(".group-bar")).toMatch(/min-width\s*:\s*0/);
    expect(rule(".group-bar-track")).toMatch(/grid-column\s*:\s*1\s*\/\s*-1/);
  });

  it("os cartões do potencial usam a grade com minmax(0, 1fr)", () => {
    expect(rule(".potential-cards")).toMatch(/display\s*:\s*grid/);
    expect(css).toMatch(/\.potential-cards\s*{[^}]*grid-template-columns\s*:\s*(?:repeat\(\d+,\s*)?minmax\(0,\s*1fr\)/);
  });

  it("a faixa do total e as linhas de oferta quebram (flex-wrap) em vez de estourar a largura", () => {
    expect(rule(".panel-headline")).toMatch(/flex-wrap\s*:\s*wrap/);
    expect(rule(".teaching-offers li")).toMatch(/flex-wrap\s*:\s*wrap/);
  });

  it("GRES-02: o valor do mínimo herda o tamanho e o peso do texto comum; só o total e o mínimo definido os mudam", () => {
    expect(rule(".panel-headline dd")).not.toMatch(/font-size|font-weight/);
    expect(rule(".panel-value")).toMatch(/font-size\s*:/);
    expect(rule(".panel-minimum")).toMatch(/font-weight\s*:\s*(700|bold)/);
  });

  it("o nome do grupo e a disciplina têm min-width: 0 e overflow-wrap: anywhere", () => {
    for (const selector of [".group-bar-name", ".teaching-title"]) {
      expect(rule(selector), selector).toMatch(/min-width\s*:\s*0/);
      expect(rule(selector), selector).toMatch(/overflow-wrap\s*:\s*anywhere/);
    }
  });

  it("o tom discreto (muted) tem contraste AA (4,5:1) sobre o fundo do cartão", () => {
    const token = (name: string) => css.match(new RegExp(`--${name}\\s*:\\s*#([0-9a-f]{6})`, "i"))![1];
    const luminance = (hex: string) => {
      const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
      const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
      return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
    };
    const [a, b] = [luminance(token("muted")), luminance(token("card"))].sort((x, y) => y - x);
    expect((a + 0.05) / (b + 0.05)).toBeGreaterThanOrEqual(4.5);
    expect(css).toMatch(/\.muted\s*{[^}]*color:\s*var\(--muted\)/);
  });
});

describe("GTAB-38: a lista de tabelas de pontuação cabe em 360 px e não quebra palavra em letras", () => {
  const rules = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({
    selector: m[1].replace(/@media[^{]*$/, "").trim(),
    body: m[2],
  }));
  const tbl = rules.filter((r) => r.selector.includes(".tbl-"));
  const rule = (selector: string) => rules.find((r) => r.selector === selector);
  const minHeightPx = (body: string) => {
    const m = body.match(/min-height\s*:\s*([\d.]+)(px|rem|em)/);
    return m ? toPx(m[1], m[2]) : 0;
  };

  it("o cartão da tabela quebra a palavra só onde precisa (break-word) e deixa o conteúdo encolher (min-width: 0)", () => {
    const card = rule(".tbl-card");
    expect(card).toBeDefined();
    expect(card!.body).toMatch(/overflow-wrap\s*:\s*break-word/);
    expect(card!.body).toMatch(/min-width\s*:\s*0/);
    const version = rule(".tbl-version");
    expect(version!.body).toMatch(/overflow-wrap\s*:\s*break-word/);
    expect(version!.body).toMatch(/min-width\s*:\s*0/);
  });

  it("nenhuma regra .tbl-* usa overflow-wrap: anywhere nem word-break: break-all (a causa das letras quebradas)", () => {
    expect(tbl.length).toBeGreaterThan(5);
    for (const r of tbl) {
      expect(r.body, r.selector).not.toMatch(/overflow-wrap\s*:\s*anywhere/);
      expect(r.body, r.selector).not.toMatch(/word-break\s*:\s*break-all/);
    }
  });

  it("a barra de ações quebra em linhas em vez de estourar a largura", () => {
    expect(rule(".tbl-actions")!.body).toMatch(/display\s*:\s*flex/);
    expect(rule(".tbl-actions")!.body).toMatch(/flex-wrap\s*:\s*wrap/);
    expect(rule(".tbl-badges")!.body).toMatch(/flex-wrap\s*:\s*wrap/);
  });

  it("o botão da barra e os botões dos diálogos têm alvo de toque de pelo menos 2,75 rem (44 px)", () => {
    expect(minHeightPx(rule(".tbl-actions .btn")!.body)).toBeGreaterThanOrEqual(2.75 * PX_PER_REM);
    expect(minHeightPx(rule(".modal .btn")!.body)).toBeGreaterThanOrEqual(2.75 * PX_PER_REM);
  });

  it("nenhuma regra .tbl-* impõe largura mínima, fixa ou de grade acima de 360 px", () => {
    const wide = tbl.flatMap((r) => [
      ...[...r.body.matchAll(/(?:^|[\s;])(width|min-width|flex-basis)\s*:\s*([\d.]+)(px|rem|em)/g)].map((m) => ({
        selector: r.selector,
        prop: m[1],
        px: toPx(m[2], m[3]),
      })),
      ...[...r.body.matchAll(/minmax\(\s*([\d.]+)(px|rem|em)/g)].map((m) => ({
        selector: r.selector,
        prop: "minmax",
        px: toPx(m[1], m[2]),
      })),
    ]);
    expect(wide.filter((d) => d.px > 360)).toEqual([]);
  });

  it("as regras da lista não forçam rolagem horizontal, tabela nem linha sem quebra", () => {
    for (const r of tbl) {
      expect(r.body, r.selector).not.toMatch(/overflow(-x)?\s*:\s*(auto|scroll)/);
      expect(r.body, r.selector).not.toMatch(/white-space\s*:\s*nowrap/);
      expect(r.body, r.selector).not.toMatch(/display\s*:\s*(table|inline-table)|table-layout/);
    }
  });

  it("o botão desabilitado com motivo (aria-disabled) continua legível e o motivo aparece em texto", () => {
    expect(rule('.tbl-actions .btn[aria-disabled="true"]')!.body).toMatch(/cursor\s*:\s*not-allowed/);
    expect(rule(".tbl-reason")).toBeDefined();
  });

  it("o filtro de arquivadas tem regra própria para a caixa de seleção (a regra global dos campos a esticaria)", () => {
    expect(css).toMatch(/input\s*,[^{]*{[^}]*width:\s*100%/); // the global rule exists
    const own = rule(".tbl-filter-archived input");
    expect(own).toBeDefined();
    expect(own!.body).toMatch(/width\s*:\s*auto/);
    expect(own!.body).toMatch(/display\s*:\s*inline-block/);
    expect(minHeightPx(rule(".tbl-filter-archived")!.body)).toBeGreaterThanOrEqual(2.75 * PX_PER_REM);
  });

  it("o bloco fica no fim do arquivo, depois do último @media, para não mudar o primeiro @media dos outros testes", () => {
    const first = css.indexOf(".tbl-");
    expect(first).toBeGreaterThan(css.lastIndexOf("@media"));
    const before = css.slice(0, first);
    expect(before.split("{").length).toBe(before.split("}").length); // nothing is open before the block
    expect(css.slice(first)).not.toContain("@media");
  });
});
