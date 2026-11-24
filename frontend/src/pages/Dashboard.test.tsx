import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router";
import { setCsrfToken } from "../api/client";
import { Dashboard } from "./Dashboard";
import { mockFetch } from "../test/fetchMock";

function summary(id: string, name: string, status: string, counts: [number, number, number], version = 1) {
  return {
    id,
    status,
    version,
    professor_id: `p-${id}`,
    professor_name: name,
    unit_id: "u1",
    modality: "PROMOCAO",
    start_date: "2024-11-23",
    end_date: "2026-11-23",
    interstice: { months: 24, days: 730 },
    alert_counts: { ERRO: counts[0], ALERTA: counts[1], REQUER_ANALISE_NORMATIVA: counts[2] },
  };
}

describe("UI-02: painel", () => {
  it("exibe total, totais por status e contagem de alertas por severidade de cada processo", async () => {
    mockFetch({
      "GET /api/processes": {
        status: 200,
        body: [
          summary("a", "Docente Alfa", "RASCUNHO", [2, 1, 1]),
          summary("b", "Docente Beta", "RASCUNHO", [0, 0, 0]),
          summary("c", "Docente Gama", "EM_ANDAMENTO", [0, 3, 0]),
        ],
      },
    });
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );

    const totals = await screen.findByRole("region", { name: "Totais" });
    const value = (label: string) =>
      within(totals).getByText(label).closest("div")!.querySelector("dd")!.textContent;
    expect(value("Total de processos")).toBe("3");
    expect(value("Rascunho")).toBe("2");
    expect(value("Em andamento")).toBe("1");
    expect(value("Concluído")).toBe("0");
    expect(value("Arquivado")).toBe("0");

    const alfa = screen.getByRole("listitem", { name: "Docente Alfa" });
    expect(within(alfa).getByText("Erro: 2")).toBeInTheDocument();
    expect(within(alfa).getByText("Alerta: 1")).toBeInTheDocument();
    expect(within(alfa).getByText("Requer análise normativa: 1")).toBeInTheDocument();
    expect(within(alfa).getByRole("link")).toHaveAttribute("href", "/processos/a");

    const gama = screen.getByRole("listitem", { name: "Docente Gama" });
    expect(within(gama).getByText("Em andamento")).toBeInTheDocument();
    expect(within(gama).getByText("Erro: 0")).toBeInTheDocument();
    expect(within(gama).getByText("Alerta: 3")).toBeInTheDocument();
  });
});

function setup(processes: ReturnType<typeof summary>[], routes: Parameters<typeof mockFetch>[0] = {}) {
  setCsrfToken("tok");
  const mock = mockFetch({ "GET /api/processes": { status: 200, body: processes }, ...routes });
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
  return { ...mock, user: userEvent.setup() };
}

const card = (name: string) => screen.findByRole("listitem", { name });
const total = (label: string) =>
  within(screen.getByRole("region", { name: "Totais" })).getByText(label).closest("div")!.querySelector("dd")!
    .textContent;

describe("GP-ARQ: arquivar processo no painel", () => {
  it("GP-ARQ-01/04: o botão Arquivar aparece nos processos que não estão arquivados", async () => {
    setup([summary("a", "Docente Alfa", "EM_ANDAMENTO", [0, 0, 0]), summary("b", "Docente Beta", "ARQUIVADO", [0, 0, 0])]);

    const alfa = await card("Docente Alfa");
    const beta = await card("Docente Beta");

    expect(within(alfa).getByRole("button", { name: "Arquivar processo de Docente Alfa" })).toHaveTextContent("Arquivar");
    expect(within(beta).queryByRole("button", { name: /Arquivar/ })).not.toBeInTheDocument();
  });

  it("GP-ARQ-02: o clique só abre a confirmação; nada é enviado antes", async () => {
    const { user, calls } = setup([summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0])]);

    await user.click(within(await card("Docente Alfa")).getByRole("button", { name: /Arquivar/ }));

    const dialog = screen.getByRole("dialog", { name: "Arquivar processo" });
    expect(within(dialog).getByText("Arquivar o processo de Docente Alfa? Ele fica somente leitura.")).toBeInTheDocument();
    expect(within(dialog).queryByRole("textbox")).not.toBeInTheDocument();
    expect(calls.filter((c) => c.method !== "GET")).toEqual([]);

    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls.filter((c) => c.method !== "GET")).toEqual([]);
  });

  it("GP-ARQ-03: confirmar envia ARQUIVADO com a versão atual e o card vira Arquivado sem recarregar a lista", async () => {
    const { user, calls } = setup([summary("a", "Docente Alfa", "EM_ANDAMENTO", [0, 0, 0], 4)], {
      "POST /api/processes/a/status": { status: 200, body: { id: "a", status: "ARQUIVADO", version: 5 } },
    });
    const alfaBefore = await card("Docente Alfa");
    expect(total("Arquivado")).toBe("0");

    await user.click(within(alfaBefore).getByRole("button", { name: /Arquivar/ }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Arquivar" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    const post = calls.find((c) => c.method === "POST")!;
    expect(JSON.parse(post.init!.body as string)).toEqual({ status: "ARQUIVADO", expected_version: 4 });
    const alfa = screen.getByRole("listitem", { name: "Docente Alfa" });
    expect(within(alfa).getByText("Arquivado")).toBeInTheDocument();
    expect(within(alfa).queryByRole("button", { name: /Arquivar/ })).not.toBeInTheDocument();
    expect(total("Arquivado")).toBe("1");
    expect(total("Em andamento")).toBe("0");
    expect(calls.filter((c) => c.method === "GET" && c.path === "/api/processes")).toHaveLength(1);
  });

  it("GP-ARQ-05: sem permissão (403) a mensagem aparece no modal e o card não muda", async () => {
    const { user } = setup([summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0])], {
      "POST /api/processes/a/status": {
        status: 403,
        body: { detail: "Apenas ADMIN ou o dono do processo podem arquivá-lo" },
      },
    });

    await user.click(within(await card("Docente Alfa")).getByRole("button", { name: /Arquivar/ }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Arquivar" }));

    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Apenas ADMIN ou o dono do processo podem arquivá-lo");
    expect(within(screen.getByRole("listitem", { name: "Docente Alfa" })).getByText("Rascunho")).toBeInTheDocument();
  });

  it("GP-ARQ-06: versão alterada (409) mostra o erro no modal e recarrega a lista", async () => {
    let loads = 0;
    const { user, calls } = setup([], {
      "GET /api/processes": () => {
        loads += 1;
        return { status: 200, body: [summary("a", "Docente Alfa", loads === 1 ? "RASCUNHO" : "EM_ANDAMENTO", [0, 0, 0], loads) ] };
      },
      "POST /api/processes/a/status": {
        status: 409,
        body: { detail: "O processo foi alterado por outro usuário; recarregue" },
      },
    });

    await user.click(within(await card("Docente Alfa")).getByRole("button", { name: /Arquivar/ }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Arquivar" }));

    expect(await within(await screen.findByRole("dialog")).findByRole("alert")).toHaveTextContent(
      "O processo foi alterado por outro usuário; recarregue",
    );
    await waitFor(() =>
      expect(within(screen.getByRole("listitem", { name: "Docente Alfa" })).getByText("Em andamento")).toBeInTheDocument(),
    );
    expect(calls.filter((c) => c.method === "GET" && c.path === "/api/processes")).toHaveLength(2);
  });
});

describe("CAINI-12..14: iniciar processo em rascunho pelo painel", () => {
  const start = (name: string) => ({ name: `Iniciar processo de ${name}` });
  const loadsOf = (calls: { method: string; path: string }[]) =>
    calls.filter((c) => c.method === "GET" && c.path === "/api/processes");

  it("CAINI-12: o botão Iniciar só aparece nas linhas em rascunho, com o aria-label exato", async () => {
    setup([
      summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0]),
      summary("b", "Docente Beta", "EM_ANDAMENTO", [0, 0, 0]),
      summary("c", "Docente Gama", "CONCLUIDO", [0, 0, 0]),
      summary("d", "Docente Delta", "ARQUIVADO", [0, 0, 0]),
    ]);

    const alfa = await card("Docente Alfa");
    const button = within(alfa).getByRole("button", start("Docente Alfa"));
    expect(button).toHaveTextContent("Iniciar");
    expect(button).toHaveAttribute("title", "Iniciar processo de Docente Alfa");
    for (const name of ["Docente Beta", "Docente Gama", "Docente Delta"]) {
      expect(within(await card(name)).queryByRole("button", { name: /Iniciar/ })).not.toBeInTheDocument();
    }
  });

  it("CAINI-13: confirmar usa o mesmo modal e o mesmo pedido, e a linha e a contagem mudam sem recarregar a lista", async () => {
    const { user, calls } = setup(
      [summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0], 4), summary("b", "Docente Beta", "RASCUNHO", [0, 0, 0])],
      { "POST /api/processes/a/status": { status: 200, body: { id: "a", status: "EM_ANDAMENTO", version: 5 } } },
    );
    const alfaBefore = await card("Docente Alfa");
    expect(total("Rascunho")).toBe("2");
    expect(total("Em andamento")).toBe("0");

    await user.click(within(alfaBefore).getByRole("button", start("Docente Alfa")));
    const dialog = screen.getByRole("dialog", { name: "Iniciar processo" });
    expect(
      within(dialog).getByText(
        "Depois de iniciado, o processo não volta a rascunho e cada alteração na Etapa 1 passa a pedir justificativa.",
      ),
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Iniciar" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    const post = calls.find((c) => c.method === "POST")!;
    expect(JSON.parse(post.init!.body as string)).toEqual({ status: "EM_ANDAMENTO", expected_version: 4 });
    const alfa = screen.getByRole("listitem", { name: "Docente Alfa" });
    expect(within(alfa).getByText("Em andamento")).toBeInTheDocument();
    expect(within(alfa).queryByRole("button", { name: /Iniciar/ })).not.toBeInTheDocument();
    expect(total("Rascunho")).toBe("1");
    expect(total("Em andamento")).toBe("1");
    expect(loadsOf(calls)).toHaveLength(1);
  });

  it("CAINI-14: 409 mostra a mensagem no modal e recarrega a lista", async () => {
    let loads = 0;
    const { user, calls } = setup([], {
      "GET /api/processes": () => {
        loads += 1;
        return { status: 200, body: [summary("a", "Docente Alfa", loads === 1 ? "RASCUNHO" : "EM_ANDAMENTO", [0, 0, 0], loads)] };
      },
      "POST /api/processes/a/status": { status: 409, body: { detail: "O processo foi alterado por outro usuário; recarregue" } },
    });

    await user.click(within(await card("Docente Alfa")).getByRole("button", start("Docente Alfa")));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Iniciar" }));

    expect(await within(await screen.findByRole("dialog")).findByRole("alert")).toHaveTextContent(
      "O processo foi alterado por outro usuário; recarregue",
    );
    await waitFor(() => expect(loadsOf(calls)).toHaveLength(2));
    await waitFor(() =>
      expect(within(screen.getByRole("listitem", { name: "Docente Alfa" })).getByText("Em andamento")).toBeInTheDocument(),
    );
  });
});

const PREVIEW = { documents: 12, activities: 30, generated_documents: 3 };

describe("GP-DEL: excluir processo no painel", () => {
  it("GP-DEL-01: o botão Excluir aparece em qualquer status, inclusive arquivado", async () => {
    setup([summary("a", "Docente Alfa", "CONCLUIDO", [0, 0, 0]), summary("b", "Docente Beta", "ARQUIVADO", [0, 0, 0])]);

    for (const name of ["Docente Alfa", "Docente Beta"]) {
      expect(
        within(await card(name)).getByRole("button", { name: `Excluir processo de ${name}` }),
      ).toHaveTextContent("Excluir");
    }
  });

  it("GP-DEL-02: o modal avisa que é definitivo, lista o que será apagado e nada é enviado antes de confirmar", async () => {
    const { user, calls } = setup([summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0])], {
      "GET /api/processes/a/delete-preview": { status: 200, body: PREVIEW },
    });

    await user.click(within(await card("Docente Alfa")).getByRole("button", { name: /Excluir/ }));

    const dialog = await screen.findByRole("dialog", { name: "Excluir processo" });
    expect(await within(dialog).findByText("12 documentos de entrada")).toBeInTheDocument();
    expect(within(dialog).getByText("30 atividades")).toBeInTheDocument();
    expect(within(dialog).getByText("3 documentos gerados")).toBeInTheDocument();
    expect(within(dialog).getByText(/A exclusão é definitiva/)).toBeInTheDocument();
    expect(within(dialog).queryByRole("textbox")).not.toBeInTheDocument();
    expect(calls.filter((c) => c.method === "DELETE")).toEqual([]);

    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls.filter((c) => c.method === "DELETE")).toEqual([]);
  });

  it("GP-DEL-02: o botão Excluir definitivamente só habilita depois da prévia", async () => {
    setup([summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0])], {
      "GET /api/processes/a/delete-preview": { status: 200, body: PREVIEW },
    });
    const user = userEvent.setup();

    await user.click(within(await card("Docente Alfa")).getByRole("button", { name: /Excluir/ }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("12 documentos de entrada");

    expect(within(dialog).getByRole("button", { name: "Excluir definitivamente" })).toBeEnabled();
  });

  it("GP-DEL-08: confirmar chama DELETE, o card sai da lista e os totais caem sem recarregar", async () => {
    const { user, calls } = setup(
      [summary("a", "Docente Alfa", "EM_ANDAMENTO", [0, 0, 0]), summary("b", "Docente Beta", "RASCUNHO", [0, 0, 0])],
      {
        "GET /api/processes/a/delete-preview": { status: 200, body: PREVIEW },
        "DELETE /api/processes/a": { status: 204, body: undefined },
      },
    );
    const alfaBefore = await card("Docente Alfa");
    expect(total("Total de processos")).toBe("2");

    await user.click(within(alfaBefore).getByRole("button", { name: /Excluir/ }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("12 documentos de entrada");
    await user.click(within(dialog).getByRole("button", { name: "Excluir definitivamente" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(calls.filter((c) => c.method === "DELETE").map((c) => c.path)).toEqual(["/api/processes/a"]);
    expect(screen.queryByRole("listitem", { name: "Docente Alfa" })).not.toBeInTheDocument();
    expect(screen.getByRole("listitem", { name: "Docente Beta" })).toBeInTheDocument();
    expect(total("Total de processos")).toBe("1");
    expect(total("Em andamento")).toBe("0");
    expect(calls.filter((c) => c.method === "GET" && c.path === "/api/processes")).toHaveLength(1);
  });

  it("GP-DEL-06: sem permissão (403) a mensagem aparece no modal e o card continua", async () => {
    const { user } = setup([summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0])], {
      "GET /api/processes/a/delete-preview": { status: 200, body: PREVIEW },
      "DELETE /api/processes/a": { status: 403, body: { detail: "Apenas ADMIN ou o dono do processo podem excluí-lo" } },
    });

    await user.click(within(await card("Docente Alfa")).getByRole("button", { name: /Excluir/ }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("12 documentos de entrada");
    await user.click(within(dialog).getByRole("button", { name: "Excluir definitivamente" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Apenas ADMIN ou o dono do processo podem excluí-lo");
    expect(screen.getByRole("listitem", { name: "Docente Alfa" })).toBeInTheDocument();
  });

  it("GP-DEL-07: operação em andamento (409) mostra o texto legível e nada sai da lista", async () => {
    const { user } = setup([summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0])], {
      "GET /api/processes/a/delete-preview": { status: 200, body: PREVIEW },
      "DELETE /api/processes/a": { status: 409, body: { detail: "x", code: "OPERACAO_EM_ANDAMENTO" } },
    });

    await user.click(within(await card("Docente Alfa")).getByRole("button", { name: /Excluir/ }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("12 documentos de entrada");
    await user.click(within(dialog).getByRole("button", { name: "Excluir definitivamente" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Há geração, redação ou leitura de documento em andamento. Espere terminar.",
    );
    expect(screen.getByRole("listitem", { name: "Docente Alfa" })).toBeInTheDocument();
  });

  it("Edge: 404 na exclusão é tratado como já excluído e a lista é recarregada", async () => {
    let loads = 0;
    const { user, calls } = setup([], {
      "GET /api/processes": () => {
        loads += 1;
        return { status: 200, body: loads === 1 ? [summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0])] : [] };
      },
      "GET /api/processes/a/delete-preview": { status: 200, body: PREVIEW },
      "DELETE /api/processes/a": { status: 404, body: { detail: "Processo não encontrado" } },
    });

    await user.click(within(await card("Docente Alfa")).getByRole("button", { name: /Excluir/ }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("12 documentos de entrada");
    await user.click(within(dialog).getByRole("button", { name: "Excluir definitivamente" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.queryByRole("listitem", { name: "Docente Alfa" })).not.toBeInTheDocument();
    expect(calls.filter((c) => c.method === "GET" && c.path === "/api/processes")).toHaveLength(2);
  });

  it("falha ao carregar a prévia mostra o erro e não oferece a exclusão", async () => {
    const { user } = setup([summary("a", "Docente Alfa", "RASCUNHO", [0, 0, 0])], {
      "GET /api/processes/a/delete-preview": { status: 403, body: { detail: "Apenas ADMIN ou o dono do processo" } },
    });

    await user.click(within(await card("Docente Alfa")).getByRole("button", { name: /Excluir/ }));
    const dialog = await screen.findByRole("dialog");

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Apenas ADMIN ou o dono do processo");
    expect(within(dialog).getByRole("button", { name: "Excluir definitivamente" })).toBeDisabled();
  });
});
