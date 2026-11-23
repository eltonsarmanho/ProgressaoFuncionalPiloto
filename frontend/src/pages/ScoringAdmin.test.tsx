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

  it("GTAB-15, GTAB-35: o ADMIN vê os botões de escrita no cartão; o cartão de critérios não traz mais os formulários", async () => {
    renderAdmin("ADMIN");
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(within(fasi).getByRole("button", { name: "Duplicar a tabela Tabela da FASI" })).toBeInTheDocument();
    expect(within(fasi).getByRole("button", { name: "Importar CSV para a tabela Tabela da FASI" })).toBeInTheDocument();
    expect(within(fasi).getByRole("button", { name: "Nova versão a partir de FASI 2026" })).toBeInTheDocument();

    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));

    const criteria = await screen.findByRole("region", { name: "Critérios de Tabela da FASI · FASI 2026" });
    expect(within(criteria).queryByRole("form")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Nome da nova tabela")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Criar nova versão" })).not.toBeInTheDocument();
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
    const listLoads = () => calls.filter((c) => c.method === "GET" && c.path === "/api/scoring-tables").length;
    expect(listLoads()).toBe(1);

    await user.click(within(fasi).getByRole("button", { name: "Duplicar a tabela Tabela da FASI" }));
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

    await user.click(within(fasi).getByRole("button", { name: "Duplicar a tabela Tabela da FASI" }));
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

    await user.click(within(fasi).getByRole("button", { name: "Duplicar a tabela Tabela da FASI" }));
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

    await user.click(within(fasi).getByRole("button", { name: "Duplicar a tabela Tabela da FASI" }));
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

describe("GTAB-14, GTAB-16, GTAB-35: unidades da tabela pela página", () => {
  it("só o ADMIN vê 'Unidades' em cada tabela", async () => {
    renderAdmin("DOCENTE");
    await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(screen.queryByRole("button", { name: /^Unidades da tabela/ })).not.toBeInTheDocument();
  });

  it("o ADMIN troca as unidades: o PUT sai, o diálogo fecha, a lista recarrega e o status anuncia", async () => {
    let loads = 0;
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: TABLES };
      },
      "PUT /api/scoring-tables/t-fasi/units": { status: 200, body: TABLES[0] },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    const opener = within(fasi).getByRole("button", { name: "Unidades da tabela Tabela da FASI" });

    await user.click(opener);
    const dialog = await screen.findByRole("dialog", { name: "Unidades da tabela Tabela da FASI" });
    await user.click(within(dialog).getByRole("checkbox", { name: "ICEN" }));
    await user.click(within(dialog).getByRole("button", { name: "Salvar unidades" }));

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await vi.waitFor(() => expect(loads).toBe(2));
    const put = calls.find((c) => c.method === "PUT" && c.path === "/api/scoring-tables/t-fasi/units");
    expect(JSON.parse(String(put?.init?.body))).toEqual({ unit_ids: ["u1", "u3"] });
    const pageStatus = screen.getAllByRole("status").find((el) => el.tagName === "P") as HTMLElement;
    expect(pageStatus).toHaveTextContent('Unidades da tabela "Tabela da FASI" atualizadas.');
    expect(opener).toHaveFocus();
  });
});

describe("GTAB-12, GTAB-13, GTAB-16, GTAB-35: duplicar, nova versão e CSV em diálogos", () => {
  const pageStatus = () => screen.getAllByRole("status").find((el) => el.tagName === "P") as HTMLElement;

  it("cada botão abre o diálogo certo", async () => {
    renderAdmin("ADMIN");
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Duplicar a tabela Tabela da FASI" }));
    expect(await screen.findByRole("dialog", { name: "Duplicar tabela" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fechar" }));

    await user.click(within(fasi).getByRole("button", { name: "Importar CSV para a tabela Tabela da FASI" }));
    expect(await screen.findByRole("dialog", { name: "Importar CSV como nova versão" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fechar" }));

    await user.click(within(fasi).getByRole("button", { name: "Nova versão a partir de FASI 2022" }));
    expect(await screen.findByRole("dialog", { name: "Nova versão a partir de FASI 2022" })).toBeInTheDocument();
  });

  it("a nova versão leva o source_version_id da versão clicada, recarrega a lista sem recarregar a página e anuncia em texto", async () => {
    let loads = 0;
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: TABLES };
      },
      "POST /api/scoring-tables/t-fasi/versions": { status: 201, body: { id: "v-new" } },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Nova versão a partir de FASI 2022" }));
    const dialog = await screen.findByRole("dialog", { name: "Nova versão a partir de FASI 2022" });
    await user.type(within(dialog).getByLabelText("Início da vigência da nova versão"), "2027-01-01");
    await user.type(within(dialog).getByLabelText("Referência normativa da nova versão"), "Res. sintética 5");
    await user.click(within(dialog).getByRole("button", { name: "Criar nova versão" }));

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await vi.waitFor(() => expect(loads).toBe(2));
    const post = calls.find((c) => c.method === "POST" && c.path === "/api/scoring-tables/t-fasi/versions");
    expect(JSON.parse(String(post?.init?.body))).toEqual({
      source_version_id: "v-fasi",
      valid_from: "2027-01-01",
      norm_reference: "Res. sintética 5",
    });
    expect(pageStatus()).toHaveTextContent("Nova versão criada.");
  });

  it("o 409 de sobreposição de vigência aparece como mensagem no diálogo e nada recarrega", async () => {
    let loads = 0;
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: TABLES };
      },
      "POST /api/scoring-tables/t-fasi/versions": {
        status: 409,
        body: { detail: "A vigência se sobrepõe à da versão FASI 2026" },
      },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Nova versão a partir de FASI 2026" }));
    const dialog = await screen.findByRole("dialog", { name: "Nova versão a partir de FASI 2026" });
    await user.type(within(dialog).getByLabelText("Início da vigência da nova versão"), "2026-06-01");
    await user.type(within(dialog).getByLabelText("Referência normativa da nova versão"), "Res. 1");
    await user.click(within(dialog).getByRole("button", { name: "Criar nova versão" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("A vigência se sobrepõe à da versão FASI 2026");
    expect(screen.getByRole("dialog", { name: "Nova versão a partir de FASI 2026" })).toBeInTheDocument();
    expect(loads).toBe(1);
  });

  it("CSV com linhas inválidas lista todas as linhas e campos, não cria nada e não recarrega a lista", async () => {
    let loads = 0;
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: TABLES };
      },
      "POST /api/scoring-tables/t-fasi/versions/import": {
        status: 422,
        body: {
          detail: [
            { field: "file", message: "linha 2, campo grupo: deve estar entre 1 e 8" },
            { field: "file", message: "linha 4, campo pontos: número decimal inválido" },
          ],
        },
      },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Importar CSV para a tabela Tabela da FASI" }));
    const dialog = await screen.findByRole("dialog", { name: "Importar CSV como nova versão" });
    await user.upload(within(dialog).getByLabelText("Arquivo CSV"), new File(["grupo,item\n"], "c.csv", { type: "text/csv" }));
    await user.type(within(dialog).getByLabelText("Início da vigência do CSV"), "2027-01-01");
    await user.type(within(dialog).getByLabelText("Referência normativa do CSV"), "Res. 2");
    await user.click(within(dialog).getByRole("button", { name: "Importar CSV" }));

    const alert = await within(dialog).findByRole("alert");
    expect(within(alert).getAllByRole("listitem").map((i) => i.textContent)).toEqual([
      "linha 2, campo grupo: deve estar entre 1 e 8",
      "linha 4, campo pontos: número decimal inválido",
    ]);
    expect(loads).toBe(1);
    expect(calls.filter((c) => c.method === "POST").map((c) => c.path)).toEqual([
      "/api/scoring-tables/t-fasi/versions/import",
    ]);
  });

  it("quem não é ADMIN não vê nenhum dos três botões", async () => {
    renderAdmin("SECRETARIA");
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(within(fasi).queryByRole("button", { name: /^Duplicar/ })).not.toBeInTheDocument();
    expect(within(fasi).queryByRole("button", { name: /^Importar CSV/ })).not.toBeInTheDocument();
    expect(within(fasi).queryByRole("button", { name: /^Nova versão/ })).not.toBeInTheDocument();
  });
});

describe("GTAB-02, GTAB-04, GTAB-10, GTAB-16, GTAB-36: definir como em uso e remover a marcação", () => {
  const pageStatus = () => screen.getAllByRole("status").find((el) => el.tagName === "P") as HTMLElement;
  const versionOf = (card: HTMLElement, name: string) =>
    Array.from(card.querySelectorAll(".tbl-version")).find((v) => v.textContent?.includes(name)) as HTMLElement;
  const MOVED = [
    {
      ...TABLES[0],
      versions: [
        { ...FASI_V1, default_for_unit_ids: [] },
        { ...FASI_V2, default_for_unit_ids: ["u1"] },
      ],
    },
    TABLES[1],
  ];

  it("com uma unidade o clique envia o PUT na hora e a etiqueta 'Em uso (FASI)' passa para a versão nova", async () => {
    let loads = 0;
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? TABLES : MOVED };
      },
      "PUT /api/scoring-units/u1/default-version": { status: 200, body: { unit_id: "u1", version_id: "v-fasi-2" } },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(versionOf(fasi, "FASI 2022")).toHaveTextContent("Em uso (FASI)");

    await user.click(within(fasi).getByRole("button", { name: "Definir FASI 2026 como em uso" }));

    await vi.waitFor(() => expect(versionOf(fasi, "FASI 2026")).toHaveTextContent("Em uso (FASI)"));
    expect(versionOf(fasi, "FASI 2022")).not.toHaveTextContent("Em uso (FASI)");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    const put = calls.find((c) => c.method === "PUT");
    expect(put?.path).toBe("/api/scoring-units/u1/default-version");
    expect(JSON.parse(String(put?.init?.body))).toEqual({ version_id: "v-fasi-2" });
    expect(pageStatus()).toHaveTextContent("FASI 2026 é agora a versão em uso de FASI.");
  });

  it("'Remover marcação de FASI' envia o DELETE e a etiqueta some", async () => {
    let loads = 0;
    const cleared = [{ ...TABLES[0], versions: [{ ...FASI_V1, default_for_unit_ids: [] }, FASI_V2] }, TABLES[1]];
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? TABLES : cleared };
      },
      "DELETE /api/scoring-units/u1/default-version": { status: 204 },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Remover marcação de FASI em FASI 2022" }));

    await vi.waitFor(() => expect(versionOf(fasi, "FASI 2022")).not.toHaveTextContent("Em uso (FASI)"));
    expect(calls.some((c) => c.method === "DELETE" && c.path === "/api/scoring-units/u1/default-version")).toBe(true);
    expect(pageStatus()).toHaveTextContent("Marcação de FASI removida; a sugestão volta a seguir a vigência.");
    expect(within(fasi).queryByRole("button", { name: /^Remover marcação/ })).not.toBeInTheDocument();
  });

  it("com duas unidades o diálogo pergunta qual, mostra desabilitada a que já tem a versão e envia só a escolhida", async () => {
    let loads = 0;
    const two = [{ ...TABLES[0], unit_ids: ["u1", "u2"] }, TABLES[1]];
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: two };
      },
      "PUT /api/scoring-units/u2/default-version": { status: 200, body: { unit_id: "u2", version_id: "v-fasi" } },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Definir FASI 2022 como em uso" }));

    const dialog = await screen.findByRole("dialog", { name: "Definir FASI 2022 como em uso" });
    expect(within(dialog).getByRole("radio", { name: /FASI/ })).toBeDisabled();
    expect(calls.some((c) => c.method === "PUT")).toBe(false);
    await user.click(within(dialog).getByRole("radio", { name: "IFCH" }));
    await user.click(within(dialog).getByRole("button", { name: "Definir como em uso" }));

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await vi.waitFor(() => expect(loads).toBe(2));
    expect(calls.filter((c) => c.method === "PUT").map((c) => c.path)).toEqual(["/api/scoring-units/u2/default-version"]);
    expect(pageStatus()).toHaveTextContent("FASI 2022 é agora a versão em uso de IFCH.");
  });

  it("o botão fica desabilitado, com o motivo, na versão que já é a em uso de todas as unidades", async () => {
    const { calls } = renderAdmin("ADMIN");
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    const button = within(fasi).getByRole("button", { name: "Definir FASI 2022 como em uso" });

    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(versionOf(fasi, "FASI 2022")).toHaveTextContent("A versão já é a em uso de todas as unidades da tabela.");
    await user.click(button);
    expect(calls.some((c) => c.method === "PUT")).toBe(false);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("o botão fica desabilitado, com o motivo, em versão substituída, em tabela arquivada e em tabela sem unidade", async () => {
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": {
        status: 200,
        body: [
          {
            ...TABLES[0],
            versions: [{ ...FASI_V1, default_for_unit_ids: [], superseded_by_id: "v-fasi-2" }, FASI_V2],
          },
          { ...OLD_TABLE, id: "t-arch", name: "Tabela arquivada", unit_ids: ["u1"], versions: [{ ...OLD_TABLE.versions[0], id: "v-arch", superseded_by_id: null }] },
          { ...TABLES[1], unit_ids: [] },
        ],
      },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    expect(within(fasi).getByRole("button", { name: "Definir FASI 2022 como em uso" })).toHaveAttribute("aria-disabled", "true");
    expect(versionOf(fasi, "FASI 2022")).toHaveTextContent("A versão foi substituída por outra");
    expect(within(fasi).getByRole("button", { name: "Definir FASI 2026 como em uso" })).not.toHaveAttribute("aria-disabled");

    const ifch = screen.getByRole("region", { name: "Tabela do IFCH" });
    expect(within(ifch).getByRole("button", { name: "Definir IFCH 2015 como em uso" })).toHaveAttribute("aria-disabled", "true");
    expect(ifch).toHaveTextContent("Associe uma unidade à tabela antes de definir como em uso.");

    await user.click(screen.getByRole("checkbox", { name: "Mostrar arquivadas" }));
    const arch = await screen.findByRole("region", { name: "Tabela arquivada" });
    expect(within(arch).getByRole("button", { name: "Definir Antiga 2015 como em uso" })).toHaveAttribute("aria-disabled", "true");
    expect(arch).toHaveTextContent("A tabela está arquivada; desarquive-a");
  });

  it("o 409 da API aparece como texto no status e a etiqueta não muda", async () => {
    renderAdmin("ADMIN", {
      "PUT /api/scoring-units/u1/default-version": {
        status: 409,
        body: { detail: "A versão foi substituída por outra", code: "VERSAO_SUBSTITUIDA" },
      },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Definir FASI 2026 como em uso" }));

    await vi.waitFor(() => expect(pageStatus()).toHaveTextContent("A versão foi substituída por outra"));
    expect(versionOf(fasi, "FASI 2022")).toHaveTextContent("Em uso (FASI)");
  });

  it("quem não é ADMIN não vê 'Definir como em uso' nem 'Remover marcação'", async () => {
    renderAdmin("DOCENTE");
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(within(fasi).queryByRole("button", { name: /como em uso/ })).not.toBeInTheDocument();
    expect(within(fasi).queryByRole("button", { name: /Remover marcação/ })).not.toBeInTheDocument();
  });
});

describe("GTAB-23, GTAB-24, GTAB-25, GTAB-16, GTAB-36: arquivar e desarquivar pela página", () => {
  const pageStatus = () => screen.getAllByRole("status").find((el) => el.tagName === "P") as HTMLElement;
  const archivedFasi = { ...TABLES[0], archived: true };

  it("arquivar envia o POST, a tabela some do filtro padrão e aparece com 'Mostrar arquivadas'", async () => {
    let loads = 0;
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? TABLES : [archivedFasi, TABLES[1]] };
      },
      "POST /api/scoring-tables/t-fasi/archive": { status: 200, body: archivedFasi },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Arquivar a tabela Tabela da FASI" }));

    await vi.waitFor(() => expect(screen.queryByRole("region", { name: "Tabela da FASI" })).not.toBeInTheDocument());
    expect(calls.some((c) => c.method === "POST" && c.path === "/api/scoring-tables/t-fasi/archive")).toBe(true);
    expect(pageStatus()).toHaveTextContent('Tabela "Tabela da FASI" arquivada.');
    expect(screen.getByText("1 tabela")).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: "Mostrar arquivadas" }));
    const shown = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(shown).toHaveTextContent("Arquivada");
  });

  it("desarquivar a devolve à lista", async () => {
    let loads = 0;
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? [archivedFasi, TABLES[1]] : TABLES };
      },
      "POST /api/scoring-tables/t-fasi/unarchive": { status: 200, body: TABLES[0] },
    });
    const user = userEvent.setup();
    await screen.findByRole("region", { name: "Tabela do IFCH" });
    await user.click(screen.getByRole("checkbox", { name: "Mostrar arquivadas" }));
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(within(fasi).queryByRole("button", { name: /^Arquivar a tabela/ })).not.toBeInTheDocument();

    await user.click(within(fasi).getByRole("button", { name: "Desarquivar a tabela Tabela da FASI" }));

    await vi.waitFor(() => expect(pageStatus()).toHaveTextContent('Tabela "Tabela da FASI" desarquivada.'));
    expect(calls.some((c) => c.method === "POST" && c.path === "/api/scoring-tables/t-fasi/unarchive")).toBe(true);
    await vi.waitFor(() => expect(screen.getByRole("region", { name: "Tabela da FASI" })).not.toHaveTextContent("Arquivada"));
  });

  it("a tabela com versão em uso tem o botão desabilitado, com o motivo e as siglas", async () => {
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": {
        status: 200,
        body: [{ ...TABLES[0], archive_blocked_reason: "TABELA_COM_VERSAO_EM_USO" }, TABLES[1]],
      },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    const button = within(fasi).getByRole("button", { name: "Arquivar a tabela Tabela da FASI" });

    expect(button).toHaveAttribute("aria-disabled", "true");
    const reason = document.getElementById(button.getAttribute("aria-describedby") as string) as HTMLElement;
    expect(reason).toHaveTextContent("A tabela tem versão em uso da unidade FASI; marque outra tabela ou desmarque a versão antes de arquivar ou excluir.");
    await user.click(button);
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("o 409 do servidor aparece como texto no status e a lista não muda", async () => {
    renderAdmin("ADMIN", {
      "POST /api/scoring-tables/t-fasi/archive": {
        status: 409,
        body: { detail: "A tabela tem versão em uso da unidade FASI", code: "TABELA_COM_VERSAO_EM_USO" },
      },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Arquivar a tabela Tabela da FASI" }));

    await vi.waitFor(() => expect(pageStatus()).toHaveTextContent("A tabela tem versão em uso da unidade FASI"));
    expect(screen.getByRole("region", { name: "Tabela da FASI" })).toBeInTheDocument();
  });

  it("quem não é ADMIN não vê 'Arquivar' nem 'Desarquivar'", async () => {
    renderAdmin("SECRETARIA");
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(within(fasi).queryByRole("button", { name: /arquivar/i })).not.toBeInTheDocument();
  });
});

describe("GTAB-16, GTAB-27, GTAB-29, GTAB-30, GTAB-36: excluir versão e tabela pela página", () => {
  const pageStatus = () => screen.getAllByRole("status").find((el) => el.tagName === "P") as HTMLElement;
  const reasonOf = (button: HTMLElement) =>
    document.getElementById(button.getAttribute("aria-describedby") as string) as HTMLElement;

  it("os botões bloqueados ficam desabilitados, com o motivo em texto e aria-describedby", async () => {
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": {
        status: 200,
        body: [
          {
            ...TABLES[0],
            delete_blocked_reason: "TABELA_COM_VERSAO_EM_USO",
            versions: [{ ...FASI_V1, delete_blocked_reason: "VERSAO_USADA_POR_PROCESSO" }, FASI_V2],
          },
          TABLES[1],
        ],
      },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    const version = within(fasi).getByRole("button", { name: "Excluir versão FASI 2022" });
    const table = within(fasi).getByRole("button", { name: "Excluir tabela Tabela da FASI" });

    expect(version).toHaveAttribute("aria-disabled", "true");
    expect(reasonOf(version)).toHaveTextContent("A versão é usada por 1 processo e não pode ser alterada nem excluída");
    expect(table).toHaveAttribute("aria-disabled", "true");
    expect(reasonOf(table)).toHaveTextContent("A tabela tem versão em uso da unidade FASI");
    await user.click(version);
    await user.click(table);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(within(fasi).getByRole("button", { name: "Excluir versão FASI 2026" })).not.toHaveAttribute("aria-disabled");
  });

  it("excluir a versão: prévia, DELETE, lista recarregada, anúncio em texto e foco no título da página", async () => {
    let loads = 0;
    const { calls } = renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? TABLES : [{ ...TABLES[0], versions: [FASI_V1] }, TABLES[1]] };
      },
      "GET /api/scoring-versions/v-fasi-2/delete-preview": { status: 200, body: { name: "FASI 2026", criteria: 5, blocked: [] } },
      "DELETE /api/scoring-versions/v-fasi-2": { status: 204 },
    });
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });

    await user.click(within(fasi).getByRole("button", { name: "Excluir versão FASI 2026" }));
    const dialog = await screen.findByRole("dialog", { name: "Excluir versão" });
    await within(dialog).findByRole("list", { name: "O que será apagado" });
    await user.click(within(dialog).getByRole("button", { name: "Excluir definitivamente" }));

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await vi.waitFor(() => expect(loads).toBe(2));
    await vi.waitFor(() =>
      expect(screen.getByRole("heading", { level: 1, name: "Tabelas de pontuação" })).toHaveFocus(),
    );
    expect(within(screen.getByRole("region", { name: "Tabela da FASI" })).queryByText("FASI 2026")).not.toBeInTheDocument();
    expect(pageStatus()).toHaveTextContent('Versão "FASI 2026" excluída.');
    expect(calls.filter((c) => c.method === "DELETE").map((c) => c.path)).toEqual(["/api/scoring-versions/v-fasi-2"]);
  });

  it("excluir a tabela: a prévia lista as unidades e, depois da confirmação, a tabela sai da lista", async () => {
    let loads = 0;
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? TABLES : [TABLES[0]] };
      },
      "GET /api/scoring-tables/t-ifch/delete-preview": {
        status: 200,
        body: { name: "Tabela do IFCH", versions: 1, criteria: 8, units: [{ id: "u2", acronym: "IFCH" }], blocked: [] },
      },
      "DELETE /api/scoring-tables/t-ifch": { status: 204 },
    });
    const user = userEvent.setup();
    const ifch = await screen.findByRole("region", { name: "Tabela do IFCH" });

    await user.click(within(ifch).getByRole("button", { name: "Excluir tabela Tabela do IFCH" }));
    const dialog = await screen.findByRole("dialog", { name: "Excluir tabela" });
    expect(await within(dialog).findByRole("list", { name: "O que será apagado" })).toHaveTextContent("Unidades associadas: IFCH");
    await user.click(within(dialog).getByRole("button", { name: "Excluir definitivamente" }));

    await vi.waitFor(() => expect(screen.queryByRole("region", { name: "Tabela do IFCH" })).not.toBeInTheDocument());
    expect(pageStatus()).toHaveTextContent('Tabela "Tabela do IFCH" excluída.');
    expect(screen.getByRole("heading", { level: 1, name: "Tabelas de pontuação" })).toHaveFocus();
  });

  it("quem não é ADMIN não vê os botões de exclusão", async () => {
    renderAdmin("DOCENTE");
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    expect(within(fasi).queryByRole("button", { name: /^Excluir/ })).not.toBeInTheDocument();
  });
});

describe("GTAB-19, GTAB-20, GTAB-22, GTAB-16: edição de critério na lista de critérios", () => {
  const pageStatus = () => screen.getAllByRole("status").find((el) => el.tagName === "P") as HTMLElement;
  const PUT_PATH = "PUT /api/scoring-versions/v-fasi-2/criteria/2/7";

  async function openCriteria() {
    const user = userEvent.setup();
    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    await user.click(within(fasi).getByRole("button", { name: "Ver critérios de FASI 2026" }));
    const criteria = await screen.findByRole("region", { name: "Critérios de Tabela da FASI · FASI 2026" });
    return { user, criteria };
  }

  it("'Editar' abre o diálogo do critério certo e o valor novo aparece na linha sem recarregar a página", async () => {
    const updated = { ...VERSION.groups[0].criteria[0], unit_points: "12.00" };
    const { calls } = renderAdmin("ADMIN", { [PUT_PATH]: { status: 200, body: updated } });
    const { user, criteria } = await openCriteria();
    const row = within(criteria).getByRole("row", { name: /Orientação de TCC/ });
    expect(row).toHaveTextContent("10,00");

    await user.click(within(row).getByRole("button", { name: "Editar critério II.7" }));
    const dialog = await screen.findByRole("dialog", { name: "Editar critério II.7" });
    const points = within(dialog).getByLabelText("Pontos por unidade");
    await user.clear(points);
    await user.type(points, "12");
    await user.type(within(dialog).getByLabelText("Referência normativa da alteração"), "Res. sintética 8");
    await user.click(within(dialog).getByRole("button", { name: "Salvar critério" }));

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(within(criteria).getByRole("row", { name: /Orientação de TCC/ })).toHaveTextContent("12,00");
    expect(pageStatus()).toHaveTextContent("Critério II.7 atualizado.");
    const put = calls.find((c) => `${c.method} ${c.path}` === PUT_PATH);
    expect(JSON.parse(String(put?.init?.body))).toEqual({
      change_reference: "Res. sintética 8",
      changes: { unit_points: 12 },
    });
    expect(calls.filter((c) => c.method === "GET" && c.path === "/api/scoring-tables")).toHaveLength(1);
    expect(calls.filter((c) => c.method === "GET" && c.path === "/api/scoring-versions/v-fasi-2")).toHaveLength(1);
  });

  it.each([
    ["VERSAO_USADA_POR_PROCESSO", "é usada por 2 processos"],
    ["VERSAO_SUBSTITUIDA", "foi substituída por outra"],
    ["VERSAO_NAO_MAIS_RECENTE", "Há uma versão mais recente da tabela"],
  ])("%s: a versão fica só leitura, com a orientação e nenhum botão de edição", async (code, orientation) => {
    renderAdmin("ADMIN", {
      "GET /api/scoring-tables": {
        status: 200,
        body: [{ ...TABLES[0], versions: [FASI_V1, { ...FASI_V2, read_only_reason: code, process_count: 2 }] }, TABLES[1]],
      },
    });
    const { criteria } = await openCriteria();

    expect(criteria).toHaveTextContent("Somente leitura");
    expect(criteria).toHaveTextContent(orientation);
    expect(within(criteria).getByText("Orientação de TCC")).toBeInTheDocument();
    expect(within(criteria).queryByRole("button", { name: /^Editar/ })).not.toBeInTheDocument();
    expect(within(criteria).queryByRole("columnheader", { name: "Ações" })).not.toBeInTheDocument();
  });

  it.each(["SECRETARIA", "DOCENTE"])("%s não vê a coluna de edição", async (role) => {
    renderAdmin(role);
    const { criteria } = await openCriteria();

    expect(within(criteria).getByText("Orientação de TCC")).toBeInTheDocument();
    expect(within(criteria).queryByRole("columnheader", { name: "Ações" })).not.toBeInTheDocument();
    expect(within(criteria).queryByRole("button", { name: /^Editar/ })).not.toBeInTheDocument();
  });
});
