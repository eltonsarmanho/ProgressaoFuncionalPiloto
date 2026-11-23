import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import { mockFetch } from "../test/fetchMock";
import { DeleteScoringDialog, type DeleteTarget } from "./DeleteScoringDialog";

const VERSION_TARGET: DeleteTarget = { kind: "version", id: "v1", name: "Sintética 2026" };
const TABLE_TARGET: DeleteTarget = { kind: "table", id: "t1", name: "Tabela sintética A" };

const VERSION_PREVIEW = { name: "Sintética 2026", criteria: 12, blocked: [] };
const TABLE_PREVIEW = {
  name: "Tabela sintética A",
  versions: 2,
  criteria: 24,
  units: [
    { id: "u2", acronym: "IFCH" },
    { id: "u1", acronym: "FASI" },
  ],
  blocked: [],
};

function setup(target: DeleteTarget, routes: Parameters<typeof mockFetch>[0]) {
  setCsrfToken("csrf-abc");
  const mock = mockFetch({ ...routes });
  const onDeleted = vi.fn();
  const onClose = vi.fn();
  render(<DeleteScoringDialog target={target} onDeleted={onDeleted} onClose={onClose} />);
  return { ...mock, onDeleted, onClose, user: userEvent.setup() };
}

const confirmButton = () => screen.getByRole("button", { name: "Excluir definitivamente" });

describe("GTAB-27, GTAB-29, GTAB-30, GTAB-16, GTAB-35: excluir versão com prévia", () => {
  const routes = { "GET /api/scoring-versions/v1/delete-preview": { status: 200, body: VERSION_PREVIEW } };

  it("diz que a exclusão é definitiva, mostra 'Carregando…' e só habilita o botão depois da prévia", async () => {
    setup(VERSION_TARGET, routes);

    const dialog = screen.getByRole("dialog", { name: "Excluir versão" });
    expect(dialog).toHaveTextContent("A exclusão é definitiva");
    expect(screen.getByText("Carregando…")).toBeInTheDocument();
    expect(confirmButton()).toBeDisabled();

    const list = await screen.findByRole("list", { name: "O que será apagado" });
    expect(within(list).getAllByRole("listitem").map((i) => i.textContent)).toEqual([
      "Versão: Sintética 2026",
      "12 critérios",
    ]);
    expect(confirmButton()).toBeEnabled();
    expect(screen.queryByText("Carregando…")).not.toBeInTheDocument();
  });

  it("a prévia com um só critério usa o singular", async () => {
    setup(VERSION_TARGET, {
      "GET /api/scoring-versions/v1/delete-preview": { status: 200, body: { ...VERSION_PREVIEW, criteria: 1 } },
    });

    const list = await screen.findByRole("list", { name: "O que será apagado" });
    expect(within(list).getAllByRole("listitem")[1]).toHaveTextContent(/^1 critério$/);
  });

  it("confirmar envia o DELETE com o token CSRF e entrega a frase de confirmação", async () => {
    const { calls, onDeleted, user } = setup(VERSION_TARGET, {
      ...routes,
      "DELETE /api/scoring-versions/v1": { status: 204 },
    });
    await screen.findByRole("list", { name: "O que será apagado" });

    await user.click(confirmButton());

    await vi.waitFor(() => expect(onDeleted).toHaveBeenCalledWith('Versão "Sintética 2026" excluída.'));
    const del = calls.find((c) => c.method === "DELETE");
    expect(del?.path).toBe("/api/scoring-versions/v1");
    expect(new Headers(del?.init?.headers).get("X-CSRF-Token")).toBe("csrf-abc");
  });

  it("com bloqueio mostra o motivo em texto, com a quantidade de processos, e mantém o botão desabilitado", async () => {
    const { calls } = setup(VERSION_TARGET, {
      "GET /api/scoring-versions/v1/delete-preview": {
        status: 200,
        body: {
          ...VERSION_PREVIEW,
          blocked: [{ code: "VERSAO_USADA_POR_PROCESSO", message: "texto do servidor", count: 3, acronyms: [] }],
        },
      },
    });

    const reasons = await screen.findByRole("list", { name: "Por que não pode ser excluída" });

    expect(reasons).toHaveTextContent("A versão é usada por 3 processos e não pode ser alterada nem excluída");
    expect(reasons).not.toHaveTextContent("VERSAO_USADA_POR_PROCESSO");
    expect(confirmButton()).toBeDisabled();
    expect(calls.map((c) => c.method)).toEqual(["GET"]);
  });

  it("o bloqueio por versão em uso cita as siglas das unidades", async () => {
    setup(VERSION_TARGET, {
      "GET /api/scoring-versions/v1/delete-preview": {
        status: 200,
        body: {
          ...VERSION_PREVIEW,
          blocked: [{ code: "VERSAO_EM_USO_DE_UNIDADE", message: "x", count: null, acronyms: ["IFCH", "FASI"] }],
        },
      },
    });

    expect(await screen.findByRole("list", { name: "Por que não pode ser excluída" })).toHaveTextContent(
      "A versão está em uso das unidades FASI, IFCH",
    );
  });

  it("404 no DELETE é tratado como já excluído, sem erro", async () => {
    const { onDeleted, user } = setup(VERSION_TARGET, {
      ...routes,
      "DELETE /api/scoring-versions/v1": { status: 404, body: { detail: "Versão não encontrada" } },
    });
    await screen.findByRole("list", { name: "O que será apagado" });

    await user.click(confirmButton());

    await vi.waitFor(() => expect(onDeleted).toHaveBeenCalledWith('A versão "Sintética 2026" já tinha sido excluída.'));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("o 409 do próprio DELETE mostra o texto e não entrega a exclusão", async () => {
    const { onDeleted, user } = setup(VERSION_TARGET, {
      ...routes,
      "DELETE /api/scoring-versions/v1": {
        status: 409,
        body: { detail: "A versão é usada por 1 processo", code: "VERSAO_USADA_POR_PROCESSO" },
      },
    });
    await screen.findByRole("list", { name: "O que será apagado" });

    await user.click(confirmButton());

    expect(await screen.findByRole("alert")).toHaveTextContent("A versão é usada por 1 processo");
    expect(onDeleted).not.toHaveBeenCalled();
    expect(confirmButton()).toBeEnabled();
  });

  it("se a prévia falha mostra o erro e o botão segue desabilitado", async () => {
    setup(VERSION_TARGET, {
      "GET /api/scoring-versions/v1/delete-preview": { status: 500, body: { detail: "Falha no servidor" } },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("Falha no servidor");
    expect(confirmButton()).toBeDisabled();
  });

  it("Esc e 'Fechar' e 'Cancelar' fecham o diálogo sem excluir", async () => {
    const { calls, onClose, user } = setup(VERSION_TARGET, routes);
    await screen.findByRole("list", { name: "O que será apagado" });

    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Fechar" }));
    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onClose).toHaveBeenCalledTimes(3);
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
  });
});

describe("GTAB-28, GTAB-30, GTAB-35: excluir tabela com prévia", () => {
  const routes = { "GET /api/scoring-tables/t1/delete-preview": { status: 200, body: TABLE_PREVIEW } };

  it("o diálogo da tabela lista o nome, as versões, os critérios e as siglas ordenadas das unidades", async () => {
    setup(TABLE_TARGET, routes);

    expect(screen.getByRole("dialog", { name: "Excluir tabela" })).toHaveTextContent("A exclusão é definitiva");
    const list = await screen.findByRole("list", { name: "O que será apagado" });
    expect(within(list).getAllByRole("listitem").map((i) => i.textContent)).toEqual([
      "Tabela: Tabela sintética A",
      "2 versões",
      "24 critérios",
      "Unidades associadas: FASI, IFCH",
    ]);
  });

  it("sem unidades a lista diz que nenhuma está associada", async () => {
    setup(TABLE_TARGET, {
      "GET /api/scoring-tables/t1/delete-preview": { status: 200, body: { ...TABLE_PREVIEW, units: [] } },
    });

    const list = await screen.findByRole("list", { name: "O que será apagado" });
    expect(within(list).getAllByRole("listitem")[3]).toHaveTextContent("Nenhuma unidade associada");
  });

  it("confirmar envia o DELETE da tabela e entrega a frase de confirmação", async () => {
    const { calls, onDeleted, user } = setup(TABLE_TARGET, {
      ...routes,
      "DELETE /api/scoring-tables/t1": { status: 204 },
    });
    await screen.findByRole("list", { name: "O que será apagado" });

    await user.click(confirmButton());

    await vi.waitFor(() => expect(onDeleted).toHaveBeenCalledWith('Tabela "Tabela sintética A" excluída.'));
    expect(calls.find((c) => c.method === "DELETE")?.path).toBe("/api/scoring-tables/t1");
  });

  it("a tabela oficial protegida mostra o motivo e não deixa excluir", async () => {
    setup(TABLE_TARGET, {
      "GET /api/scoring-tables/t1/delete-preview": {
        status: 200,
        body: {
          ...TABLE_PREVIEW,
          blocked: [{ code: "TABELA_OFICIAL_PROTEGIDA", message: "x", count: null, acronyms: [] }],
        },
      },
    });

    expect(await screen.findByRole("list", { name: "Por que não pode ser excluída" })).toHaveTextContent(
      "A tabela oficial da UFPA e as suas versões não podem ser excluídas",
    );
    expect(confirmButton()).toBeDisabled();
  });

  it("404 no DELETE da tabela é tratado como já excluída", async () => {
    const { onDeleted, user } = setup(TABLE_TARGET, {
      ...routes,
      "DELETE /api/scoring-tables/t1": { status: 404, body: { detail: "x" } },
    });
    await screen.findByRole("list", { name: "O que será apagado" });

    await user.click(confirmButton());

    await vi.waitFor(() => expect(onDeleted).toHaveBeenCalledWith('A tabela "Tabela sintética A" já tinha sido excluída.'));
  });
});
