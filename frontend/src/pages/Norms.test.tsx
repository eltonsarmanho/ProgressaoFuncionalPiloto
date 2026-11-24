import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router";
import { AppRoutes } from "../App";
import { AuthProvider } from "../auth/AuthContext";
import type { Norm } from "../api/types";
import { ME, mockFetch } from "../test/fetchMock";

const ACTIVE: Norm = {
  id: "n1",
  code: "LEI-SINTETICA-2012",
  title: "Lei sintética nº 1/2012",
  kind: "LEI",
  issuer: "Presidência sintética",
  published_on: "2012-12-28",
  valid_from: "2013-01-01",
  valid_to: null,
  source_url: "https://norma.exemplo.test/lei",
  notes: null,
  archived: false,
  version: 2,
  file: null,
  linked_rules: [
    { kind: "CARREIRA", name: "Estrutura sintética A", detail: null },
    { kind: "TABELA", name: "Tabela sintética B", detail: "vigência a partir de 23/11/2024" },
  ],
};
const WITH_FILE: Norm = {
  ...ACTIVE,
  id: "n2",
  code: "RES-SINTETICA-2015",
  title: "Resolução sintética nº 2/2015",
  kind: "RESOLUCAO",
  issuer: "Conselho sintético",
  published_on: "2015-03-10",
  valid_from: "2015-04-01",
  valid_to: "2024-12-31",
  source_url: "https://norma.exemplo.test/res",
  file: { original_name: "res.pdf", size_bytes: 1000, url: "/api/norms/n2/file" },
  linked_rules: [],
};
const ARCHIVED: Norm = {
  ...ACTIVE,
  id: "n3",
  code: "IN-SINTETICA-2020",
  title: "Instrução sintética nº 3/2020",
  kind: "INSTRUCAO_NORMATIVA",
  issuer: "Instituto sintético",
  published_on: "2020-06-01",
  valid_from: null,
  source_url: null,
  archived: true,
  linked_rules: [{ kind: "TITULACAO", name: "Estrutura sintética A", detail: "classe C: DOUTORADO" }],
};

function renderNorms(role: string, extra: Parameters<typeof mockFetch>[0] = {}) {
  const mock = mockFetch({
    "GET /api/auth/me": { status: 200, body: { ...ME, role } },
    "GET /api/norms?include_archived=false": { status: 200, body: [ACTIVE, WITH_FILE] },
    "GET /api/processes": { status: 200, body: [] },
    ...extra,
  });
  render(
    <MemoryRouter initialEntries={["/normas"]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
  return mock;
}

function row(title: string) {
  return screen.getByText(title).closest("tr") as HTMLElement;
}

describe("NLIST-01: a página Normas para toda pessoa autenticada", () => {
  it("DOCENTE vê título, tipo, órgão, publicação, vigência, link e regras ligadas, sem botões de edição", async () => {
    renderNorms("DOCENTE");

    expect(await screen.findByRole("heading", { name: "Normas" })).toBeInTheDocument();
    const first = row("Lei sintética nº 1/2012");
    expect(first).toHaveTextContent("Lei");
    expect(first).toHaveTextContent("Presidência sintética");
    expect(first).toHaveTextContent("28/12/2012");
    expect(first).toHaveTextContent("a partir de 01/01/2013");
    expect(first).toHaveTextContent("Estrutura de carreira: Estrutura sintética A");
    expect(first).toHaveTextContent("Tabela de pontuação: Tabela sintética B (vigência a partir de 23/11/2024)");
    expect(within(first).getByRole("link", { name: "Ver norma" })).toHaveAttribute(
      "href",
      "https://norma.exemplo.test/lei",
    );
    const second = row("Resolução sintética nº 2/2015");
    expect(second).toHaveTextContent("01/04/2015 a 31/12/2024");
    // NLINK-04: with a file attached the link goes to the file
    expect(within(second).getByRole("link", { name: "Ver norma" })).toHaveAttribute("href", "/api/norms/n2/file");

    expect(screen.queryByRole("button", { name: /Cadastrar norma/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Editar/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Anexar PDF/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Arquivar/ })).toBeNull();
  });
});

describe("NLIST-03: botões de gestão só para o ADMIN", () => {
  it("ADMIN vê Cadastrar e, em cada linha, Editar, Anexar PDF e Arquivar", async () => {
    renderNorms("ADMIN");

    expect(await screen.findByRole("button", { name: "Cadastrar norma" })).toBeInTheDocument();
    const first = row("Lei sintética nº 1/2012");
    expect(within(first).getByRole("button", { name: "Editar Lei sintética nº 1/2012" })).toBeInTheDocument();
    expect(within(first).getByRole("button", { name: "Anexar PDF a Lei sintética nº 1/2012" })).toBeInTheDocument();
    expect(within(first).getByRole("button", { name: "Arquivar Lei sintética nº 1/2012" })).toBeInTheDocument();
  });

  it("Cadastrar, Editar e Anexar PDF abrem o formulário numa janela", async () => {
    renderNorms("ADMIN");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Cadastrar norma" }));
    let dialog = await screen.findByRole("dialog", { name: "Cadastrar norma" });
    expect(within(dialog).getByLabelText("Código")).not.toHaveAttribute("readonly");
    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).toBeNull();

    await user.click(screen.getByRole("button", { name: "Editar Lei sintética nº 1/2012" }));
    dialog = await screen.findByRole("dialog", { name: "Editar norma" });
    expect(within(dialog).getByLabelText("Código")).toHaveValue("LEI-SINTETICA-2012");
    expect(within(dialog).getByLabelText("Código")).toHaveAttribute("readonly");
    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));

    await user.click(screen.getByRole("button", { name: "Anexar PDF a Lei sintética nº 1/2012" }));
    dialog = await screen.findByRole("dialog", { name: "Anexar PDF" });
    expect(within(dialog).getByLabelText("Arquivo PDF")).toBeInTheDocument();
  });
});

describe("NLIST-02: normas arquivadas", () => {
  it("a lista padrão pede include_archived=false e o filtro 'Mostrar arquivadas' pede true e mostra '(arquivada)'", async () => {
    const { calls } = renderNorms("DOCENTE", {
      "GET /api/norms?include_archived=true": { status: 200, body: [ACTIVE, WITH_FILE, ARCHIVED] },
    });
    await screen.findByText("Lei sintética nº 1/2012");
    expect(screen.queryByText("Instrução sintética nº 3/2020")).toBeNull();
    expect(calls.map((c) => c.path)).toContain("/api/norms?include_archived=false");

    await userEvent.setup().click(screen.getByLabelText("Mostrar arquivadas"));

    const archived = await screen.findByText("Instrução sintética nº 3/2020");
    expect(calls.map((c) => c.path)).toContain("/api/norms?include_archived=true");
    const tr = archived.closest("tr") as HTMLElement;
    expect(tr).toHaveTextContent("(arquivada)");
    expect(tr).toHaveTextContent("Titulação: Estrutura sintética A (classe C: DOUTORADO)");
    // NBASE-08: a norm with neither file nor URL shows only its title
    expect(within(tr).queryByRole("link")).toBeNull();
  });

  it("a norma arquivada não oferece o botão Arquivar ao ADMIN", async () => {
    renderNorms("ADMIN", {
      "GET /api/norms?include_archived=true": { status: 200, body: [ACTIVE, ARCHIVED] },
    });
    await userEvent.setup().click(await screen.findByLabelText("Mostrar arquivadas"));
    const tr = (await screen.findByText("Instrução sintética nº 3/2020")).closest("tr") as HTMLElement;
    expect(within(tr).queryByRole("button", { name: /Arquivar/ })).toBeNull();
    expect(within(tr).getByRole("button", { name: /Editar/ })).toBeInTheDocument();
  });
});

describe("NBASE-08: arquivar pede confirmação e atualiza a linha", () => {
  it("Cancelar não chama a API; confirmar envia a versão lida e a linha passa a '(arquivada)'", async () => {
    let archived = false;
    const { calls } = renderNorms("ADMIN", {
      "GET /api/norms?include_archived=true": () => ({
        status: 200,
        body: [{ ...ACTIVE, archived, version: archived ? 3 : 2 }, WITH_FILE],
      }),
      "POST /api/norms/n1/archive": () => {
        archived = true;
        return { status: 200, body: { ...ACTIVE, archived: true, version: 3 } };
      },
    });
    const user = userEvent.setup();
    await user.click(await screen.findByLabelText("Mostrar arquivadas"));
    await screen.findByText("Lei sintética nº 1/2012");

    await user.click(screen.getByRole("button", { name: "Arquivar Lei sintética nº 1/2012" }));
    let dialog = await screen.findByRole("dialog", { name: "Arquivar norma" });
    expect(dialog).toHaveTextContent("Lei sintética nº 1/2012");
    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(calls.some((c) => c.method === "POST")).toBe(false);

    await user.click(screen.getByRole("button", { name: "Arquivar Lei sintética nº 1/2012" }));
    dialog = await screen.findByRole("dialog", { name: "Arquivar norma" });
    await user.click(within(dialog).getByRole("button", { name: "Arquivar" }));

    await within(row("Lei sintética nº 1/2012")).findByText("(arquivada)");
    const post = calls.find((c) => c.method === "POST");
    expect(JSON.parse(String(post?.init?.body))).toEqual({ expected_version: 2 });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("o 409 mostra que a norma foi alterada por outra pessoa e mantém a janela aberta", async () => {
    renderNorms("ADMIN", {
      "POST /api/norms/n1/archive": { status: 409, body: { detail: "Versão desatualizada" } },
    });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Arquivar Lei sintética nº 1/2012" }));
    const dialog = await screen.findByRole("dialog", { name: "Arquivar norma" });
    await user.click(within(dialog).getByRole("button", { name: "Arquivar" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "A norma foi alterada por outra pessoa; recarregue",
    );
  });
});

describe("NLIST-01: item de menu Normas", () => {
  it.each(["DOCENTE", "ADMIN"])("o menu 'Normas' aparece para %s e aponta para /normas", async (role) => {
    renderNorms(role);
    const link = await screen.findByRole("link", { name: "Normas" });
    expect(link).toHaveAttribute("href", "/normas");
  });
});
