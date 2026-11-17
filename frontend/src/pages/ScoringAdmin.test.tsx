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
  valid_to: "2026-02-28",
  norm_reference: "Res. FASI 2022, Anexo I",
  status: "PENDENTE_VALIDACAO",
  in_use: true,
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
};
const TABLES = [
  { id: "t-fasi", name: "Tabela da FASI", archived: false, unit_ids: ["u1"], versions: [FASI_V1, FASI_V2] },
  {
    id: "t-ifch",
    name: "Tabela do IFCH",
    archived: false,
    unit_ids: ["u2"],
    versions: [
      { ...FASI_V1, id: "v-ifch", table_id: "t-ifch", name: "IFCH 2015", valid_to: null, status: "OFICIAL", norm_reference: "Res. 4.644/2015" },
    ],
  },
];

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
  it("ADMIN vê as tabelas com vigência, situação e referência de cada versão", async () => {
    renderAdmin("ADMIN");

    const fasi = await screen.findByRole("region", { name: "Tabela da FASI" });
    const rows = within(fasi).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("FASI 2022");
    expect(rows[1]).toHaveTextContent("23/11/2022 a 28/02/2026");
    expect(rows[1]).toHaveTextContent("Pendente de validação");
    expect(rows[1]).toHaveTextContent("Res. FASI 2022, Anexo I");
    expect(rows[1]).toHaveTextContent("Em uso");
    expect(rows[2]).toHaveTextContent("FASI 2026");
    expect(rows[2]).toHaveTextContent("01/03/2026 a em aberto");
    expect(rows[2]).toHaveTextContent("Oficial");
    expect(rows[2]).toHaveTextContent("Res. 7.000/2026");
    expect(screen.getByRole("region", { name: "Tabela do IFCH" })).toBeInTheDocument();
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

  it.each(["SECRETARIA", "DOCENTE"])("%s é redirecionado e não vê o link", async (role) => {
    renderAdmin(role);

    expect(await screen.findByRole("heading", { name: "Painel" })).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(/^\/$/);
    expect(screen.queryByRole("link", { name: "Tabelas de pontuação" })).not.toBeInTheDocument();
    expect(screen.queryByText("Tabela da FASI")).not.toBeInTheDocument();
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
