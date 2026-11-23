import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter, useLocation } from "react-router";
import { AppRoutes } from "../App";
import { AuthProvider } from "../auth/AuthContext";
import { ME, mockFetch } from "../test/fetchMock";

const FASI_V1 = {
  id: "v-fasi",
  table_id: "t-fasi",
  name: "FASI 2022",
  valid_from: "2022-11-23",
  valid_to: "2024-12-31",
  norm_reference: "Res. FASI 2022, Anexo I",
  status: "PENDENTE_VALIDACAO",
  superseded_by_id: null,
  in_use: true,
  process_count: 1,
  default_for_unit_ids: ["u1"],
  read_only_reason: null,
  delete_blocked_reason: null,
};
const FASI_V2 = {
  ...FASI_V1,
  id: "v-fasi-2",
  name: "FASI 2026",
  valid_from: "2026-03-01",
  valid_to: null,
  norm_reference: "Res. 7.000/2026",
  status: "OFICIAL",
  in_use: false,
  process_count: 0,
  default_for_unit_ids: [],
};
const TABLES = [
  {
    id: "t-fasi",
    name: "Tabela da FASI",
    archived: false,
    unit_ids: ["u1"],
    archive_blocked_reason: null,
    delete_blocked_reason: null,
    versions: [FASI_V1, FASI_V2],
  },
  {
    id: "t-ifch",
    name: "Tabela do IFCH",
    archived: false,
    unit_ids: ["u2"],
    archive_blocked_reason: null,
    delete_blocked_reason: null,
    versions: [
      { ...FASI_V1, id: "v-ifch", table_id: "t-ifch", name: "IFCH 2015", valid_to: null, status: "OFICIAL", norm_reference: "Res. 4.644/2015" },
    ],
  },
];

const UNITS = [
  { id: "u1", name: "Faculdade de Sistemas", acronym: "FASI", kind: "FACULDADE", parent_id: null, archived: false },
  { id: "u2", name: "Instituto de Ciências Humanas", acronym: "IFCH", kind: "INSTITUTO", parent_id: null, archived: false },
  { id: "u3", name: "Instituto sem tabelas", acronym: "ICEN", kind: "INSTITUTO", parent_id: null, archived: false },
];
const OLD_TABLE = {
  id: "t-old",
  name: "Tabela antiga",
  archived: true,
  unit_ids: [],
  archive_blocked_reason: null,
  delete_blocked_reason: null,
  versions: [
    {
      ...FASI_V1,
      id: "v-old",
      table_id: "t-old",
      name: "Antiga 2015",
      valid_to: null,
      default_for_unit_ids: [],
      in_use: false,
      process_count: 0,
      superseded_by_id: "v-fasi-2",
    },
  ],
};

const VERSION = {
  ...FASI_V2,
  minimums: null,
  notes: null,
  groups: [
    {
      number: 2,
      name: "Orientação",
      counts_in_total: true,
      max_points: null,
      criteria: [
        { group_number: 2, item_number: 7, description: "Orientação de TCC", unit_label: "orientação", mode: "POR_UNIDADE", unit_points: "10.00", hours_per_block: null, weeks_per_semester: null, prep_ratio: null, max_points: "30.00", accepted_evidence: null, rules: null, review_note: null },
      ],
    },
  ],
};

function LocationProbe() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}

function renderAdmin(role: string, extra: Parameters<typeof mockFetch>[0] = {}) {
  const mock = mockFetch({
    "GET /api/auth/me": { status: 200, body: { ...ME, role } },
    "GET /api/scoring-tables": { status: 200, body: TABLES },
    "GET /api/units": { status: 200, body: UNITS },
    "GET /api/scoring-versions/v-fasi-2": { status: 200, body: VERSION },
    "GET /api/processes": { status: 200, body: [] },
    ...extra,
  });
  render(
    <MemoryRouter initialEntries={["/administracao/tabelas"]}>
      <AuthProvider>
        <AppRoutes />
        <LocationProbe />
      </AuthProvider>
    </MemoryRouter>,
  );
  return mock;
}

describe("ADMUI-01: lista de tabelas e versões", () => {
  it("GTAB-33, GTAB-34: um cartão por tabela, com a vigência, a situação e a referência de cada versão", async () => {
    renderAdmin("ADMIN");

    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(fasi).toHaveClass("tbl-card");
    const versions = fasi.querySelectorAll(".tbl-version");
    expect(versions).toHaveLength(2);
    expect(versions[0]).toHaveTextContent("FASI 2022");
    expect(versions[0]).toHaveTextContent("23/11/2022 a 31/12/2024");
    expect(versions[0]).toHaveTextContent("Pendente de validação");
    expect(versions[0]).toHaveTextContent("Res. FASI 2022, Anexo I");
    expect(versions[1]).toHaveTextContent("FASI 2026");
    expect(versions[1]).toHaveTextContent("01/03/2026 a em aberto");
    expect(versions[1]).toHaveTextContent("Oficial");
    expect(versions[1]).toHaveTextContent("Res. 7.000/2026");
    expect(screen.getByRole("region", { name: "Tabela do IFCH" })).toHaveClass("tbl-card");
  });

  it("GTAB-34: 'Em uso (sigla)' e 'Encerrada' na versão marcada cuja vigência acabou, 'Usada por processo' à parte", async () => {
    renderAdmin("ADMIN");

    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    const [first, second] = Array.from(fasi.querySelectorAll(".tbl-version"));
    expect(first).toHaveTextContent("Em uso (FASI)");
    expect(first).toHaveTextContent("Encerrada");
    expect(first).toHaveTextContent("Usada por processo");
    expect(second).not.toHaveTextContent("Em uso");
    expect(second).not.toHaveTextContent("Encerrada");
    expect(second).not.toHaveTextContent("Usada por processo");
  });

  it("GTAB-34: a versão em uso e ainda vigente não é 'Encerrada', e a versão usada por processo sem marcação não é 'Em uso'", async () => {
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": {
        status: 200,
        body: [
          {
            ...TABLES[0],
            versions: [
              { ...FASI_V1, valid_to: null, default_for_unit_ids: ["u1", "u2"] },
              { ...FASI_V2, in_use: true, process_count: 2 },
            ],
          },
        ],
      },
    });

    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    const [first, second] = Array.from(fasi.querySelectorAll(".tbl-version"));
    expect(first).toHaveTextContent("Em uso (FASI)");
    expect(first).toHaveTextContent("Em uso (IFCH)");
    expect(first).not.toHaveTextContent("Encerrada");
    expect(second).toHaveTextContent("Usada por processo");
    expect(second).not.toHaveTextContent("Em uso (");
  });

  it("GTAB-34: 'Substituída' e 'Arquivada' aparecem nos casos certos", async () => {
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": { status: 200, body: [...TABLES, OLD_TABLE] },
    });
    const user = userEvent.setup();
    await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(screen.queryByRole("region", { name: "Tabela antiga" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: "Mostrar arquivadas" }));

    const old = await screen.findByRole("region", { name: "Tabela antiga" });
    expect(old).toHaveTextContent("Substituída");
    expect(old).toHaveTextContent("Arquivada");
    const fasi = screen.getByRole("region", { name: "Tabela da FASI" });
    expect(fasi).not.toHaveTextContent("Substituída");
    expect(fasi).not.toHaveTextContent("Arquivada");
  });

  it("GTAB-33: as unidades do cartão aparecem como siglas, nunca como id", async () => {
    renderAdmin("ADMIN");

    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(fasi).toHaveTextContent("Unidades: FASI");
    expect(fasi).not.toHaveTextContent("u1");
    expect(screen.getByRole("region", { name: "Tabela do IFCH" })).toHaveTextContent("Unidades: IFCH");
  });

  it("GTAB-33: a lista não usa tabela HTML dentro dos cartões", async () => {
    renderAdmin("ADMIN");

    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(fasi.querySelector("table")).toBeNull();
    expect(within(fasi).queryByRole("table")).not.toBeInTheDocument();
  });

  it("mostra os critérios da versão escolhida", async () => {
    const { calls } = renderAdmin("ADMIN");
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));

    const criteria = await screen.findByRole("region", { name: "Critérios de Tabela da FASI · FASI 2026" });
    expect(within(criteria).getByText("Orientação de TCC")).toBeInTheDocument();
    expect(criteria).toHaveTextContent("II.7");
    expect(criteria).toHaveTextContent("10,00");
    expect(calls.map((c) => `${c.method} ${c.path}`)).toContain("GET /api/scoring-versions/v-fasi-2");
  });

  it("ADMIN vê o link da administração no menu", async () => {
    renderAdmin("ADMIN");
    expect(await screen.findByRole("link", { name: "Tabelas de pontuação" })).toHaveAttribute(
      "href",
      "/administracao/tabelas",
    );
  });

  it.each(["SECRETARIA", "DOCENTE"])("GTAB-15: %s vê o link e a lista, sem nenhum botão de escrita", async (role) => {
    renderAdmin(role);
    const user = userEvent.setup();

    expect(await screen.findByRole("link", { name: "Tabelas de pontuação" })).toHaveAttribute(
      "href",
      "/administracao/tabelas",
    );
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(screen.getByTestId("location")).toHaveTextContent(/^\/administracao\/tabelas$/);
    expect(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" })).toBeInTheDocument();
    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));
    const criteria = await screen.findByRole("region", { name: "Critérios de Tabela da FASI · FASI 2026" });
    expect(within(criteria).getByText("Orientação de TCC")).toBeInTheDocument();
    for (const name of ["Duplicar tabela", "Criar nova versão", "Importar CSV"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
    expect(screen.queryByLabelText("Nome da nova tabela")).not.toBeInTheDocument();
  });

  it("GTAB-15: o ADMIN vê os formulários de escrita ao abrir os critérios", async () => {
    renderAdmin("ADMIN");
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));

    expect(await screen.findByRole("button", { name: "Duplicar tabela" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar nova versão" })).toBeInTheDocument();
  });
});

describe("ADMUI-03: revisão na tabela aberta", () => {
  it("a página destaca o critério com anotação da versão aberta", async () => {
    const marked = { ...VERSION.groups[0].criteria[0], review_note: "Valor diverge do IFCH" };
    renderAdmin("ADMIN", {
      "GET /api/scoring-versions/v-fasi-2": {
        status: 200,
        body: { ...VERSION, groups: [{ ...VERSION.groups[0], criteria: [marked] }] },
      },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));

    const row = await screen.findByRole("row", { name: /Orientação de TCC/ });
    expect(row).toHaveClass("review");
    expect(row).toHaveTextContent("Valor diverge do IFCH");
  });
});

describe("ADMUI-02: formulários na página", () => {
  it("duplicar uma tabela recarrega a lista de tabelas", async () => {
    const { calls } = renderAdmin("ADMIN", {
      "POST /api/scoring-tables/t-fasi/duplicate": { status: 201, body: { id: "t-new" } },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));
    const listLoads = () => calls.filter((c) => c.method === "GET" && c.path === "/api/scoring-tables").length;
    expect(listLoads()).toBe(1);

    await user.type(await screen.findByLabelText("Nome da nova tabela"), "Cópia da FASI");
    await user.click(screen.getByRole("button", { name: "Duplicar tabela" }));

    await vi.waitFor(() => expect(listLoads()).toBe(2));
  });
});

describe("GTAB-39, GTAB-40, GTAB-37: filtros, contagem e estados da lista", () => {
  it("filtra por unidade e conta as tabelas listadas", async () => {
    renderAdmin("ADMIN");
    const user = userEvent.setup();
    await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(screen.getByText("2 tabelas")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Filtrar por unidade"), "IFCH");

    expect(screen.getByText("1 tabela")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Tabela do IFCH" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Tabela da FASI" })).not.toBeInTheDocument();
  });

  it("'Mostrar arquivadas' vem desligado e muda a lista e a contagem", async () => {
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": { status: 200, body: [...TABLES, OLD_TABLE] },
    });
    const user = userEvent.setup();
    await screen.findByRole("region", { name: "Tabela da FASI" });
    const toggle = screen.getByRole("checkbox", { name: "Mostrar arquivadas" });
    expect(toggle).not.toBeChecked();
    expect(screen.getByText("2 tabelas")).toBeInTheDocument();

    await user.click(toggle);
    expect(screen.getByText("3 tabelas")).toBeInTheDocument();

    await user.click(toggle);
    expect(screen.getByText("2 tabelas")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Tabela antiga" })).not.toBeInTheDocument();
  });

  it("GTAB-40: sem tabela no filtro mostra a mensagem e 'Limpar filtros' restaura a lista", async () => {
    renderAdmin("ADMIN");
    const user = userEvent.setup();
    await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.selectOptions(screen.getByLabelText("Filtrar por unidade"), "ICEN");

    expect(screen.getByText("Nenhuma tabela encontrada com estes filtros.")).toBeInTheDocument();
    expect(screen.getByText("0 tabelas")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Limpar filtros" }));

    expect(screen.getByLabelText("Filtrar por unidade")).toHaveValue("");
    expect(screen.getByRole("region", { name: "Tabela da FASI" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Tabela do IFCH" })).toBeInTheDocument();
    expect(screen.getByText("2 tabelas")).toBeInTheDocument();
  });

  it("GTAB-39: mostra o carregamento enquanto a lista não chegou", async () => {
    renderAdmin("ADMIN");

    expect(screen.getByText("Carregando…")).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Tabela da FASI" })).toBeInTheDocument();
    expect(screen.queryByText("Carregando…")).not.toBeInTheDocument();
  });

  it("GTAB-39: se a carga falha mostra o erro e 'Tentar de novo' carrega a lista", async () => {
    let loads = 0;
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return loads === 1 ? { status: 500, body: { detail: "Falha no servidor" } } : { status: 200, body: TABLES };
      },
    });
    const user = userEvent.setup();

    expect(await screen.findByRole("alert")).toHaveTextContent("Falha no servidor");
    expect(screen.queryByRole("region", { name: "Tabela da FASI" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar de novo" }));

    expect(await screen.findByRole("region", { name: "Tabela da FASI" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(loads).toBe(2);
  });
});

describe("GTAB-16, GTAB-37: critérios abertos, foco e anúncio", () => {
  it("o título da página e o dos critérios aceitam foco, e abrir os critérios move o foco ao título deles", async () => {
    renderAdmin("ADMIN");
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(screen.getByRole("heading", { level: 1, name: "Tabelas de pontuação" })).toHaveAttribute("tabindex", "-1");

    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));

    const title = await screen.findByRole("heading", { name: "Critérios · Tabela da FASI · FASI 2026" });
    expect(title).toHaveAttribute("tabindex", "-1");
    expect(title).toHaveFocus();
  });

  it("recarregar a lista com a versão aberta que ficou só leitura mostra a orientação nova", async () => {
    let loads = 0;
    const used = { ...FASI_V2, in_use: true, process_count: 2, read_only_reason: "VERSAO_USADA_POR_PROCESSO" };
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? TABLES : [{ ...TABLES[0], versions: [FASI_V1, used] }, TABLES[1]] };
      },
      "POST /api/scoring-tables/t-fasi/duplicate": { status: 201, body: { id: "t-new" } },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));
    const criteria = await screen.findByRole("region", { name: "Critérios de Tabela da FASI · FASI 2026" });
    expect(criteria).not.toHaveTextContent("Somente leitura");

    await user.type(await screen.findByLabelText("Nome da nova tabela"), "Cópia da FASI");
    await user.click(screen.getByRole("button", { name: "Duplicar tabela" }));

    await vi.waitFor(() => expect(criteria).toHaveTextContent("Somente leitura"));
    expect(criteria).toHaveTextContent("é usada por 2 processos");
    expect(criteria).toHaveTextContent("crie uma nova versão");
  });

  it("recarregar a lista sem a versão aberta fecha o cartão dos critérios", async () => {
    let loads = 0;
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? TABLES : [{ ...TABLES[0], versions: [FASI_V1] }, TABLES[1]] };
      },
      "POST /api/scoring-tables/t-fasi/duplicate": { status: 201, body: { id: "t-new" } },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));
    await screen.findByRole("region", { name: "Critérios de Tabela da FASI · FASI 2026" });

    await user.type(await screen.findByLabelText("Nome da nova tabela"), "Cópia da FASI");
    await user.click(screen.getByRole("button", { name: "Duplicar tabela" }));

    await vi.waitFor(() =>
      expect(screen.queryByRole("region", { name: "Critérios de Tabela da FASI · FASI 2026" })).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("region", { name: "Tabela da FASI" })).toBeInTheDocument();
  });

  it("o parágrafo de status existe sempre e anuncia a mensagem que a página recebe", async () => {
    renderAdmin("ADMIN", {
      "POST /api/scoring-tables/t-fasi/duplicate": { status: 201, body: { id: "t-new" } },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    const pageStatus = () => screen.getAllByRole("status").find((el) => el.tagName === "P") as HTMLElement;
    expect(pageStatus()).toBeEmptyDOMElement();
    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));

    await user.type(await screen.findByLabelText("Nome da nova tabela"), "Cópia da FASI");
    await user.click(screen.getByRole("button", { name: "Duplicar tabela" }));

    await vi.waitFor(() => expect(pageStatus()).toHaveTextContent("Tabela duplicada."));
  });
});

describe("GTAB-11, GTAB-16, GTAB-35: nova tabela pela página", () => {
  it("só o ADMIN vê o botão 'Nova tabela' no cabeçalho", async () => {
    renderAdmin("SECRETARIA");
    await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(screen.queryByRole("button", { name: "Nova tabela" })).not.toBeInTheDocument();
  });

  it("o ADMIN cria a tabela: o diálogo fecha, a lista recarrega, o status anuncia e o foco volta ao botão", async () => {
    let loads = 0;
    const created = { id: "t-new", name: "Tabela nova", archived: false, unit_ids: [], archive_blocked_reason: null, delete_blocked_reason: null, versions: [] };
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? TABLES : [...TABLES, created] };
      },
      "POST /api/scoring-tables": { status: 201, body: created },
    });
    const user = userEvent.setup();
    await screen.findByRole("region", { name: "Tabela da FASI" });
    const opener = screen.getByRole("button", { name: "Nova tabela" });

    await user.click(opener);
    const dialog = await screen.findByRole("dialog", { name: "Nova tabela" });
    await user.type(within(dialog).getByLabelText("Nome da tabela"), "Tabela nova");
    await user.type(within(dialog).getByLabelText("Início da vigência"), "2026-03-01");
    await user.type(within(dialog).getByLabelText("Referência normativa"), "Res. sintética 1");
    await user.click(within(dialog).getByRole("button", { name: "Criar tabela" }));

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await vi.waitFor(() => expect(loads).toBe(2));
    expect(await screen.findByRole("region", { name: "Tabela nova" })).toBeInTheDocument();
    const pageStatus = screen.getAllByRole("status").find((el) => el.tagName === "P") as HTMLElement;
    expect(pageStatus).toHaveTextContent('Tabela "Tabela nova" criada.');
    expect(opener).toHaveFocus();
    expect(calls.filter((c) => c.method === "POST").map((c) => c.path)).toEqual(["/api/scoring-tables"]);
  });
});
