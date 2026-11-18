import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { ConclusionPreview, ConclusionResult } from "../api/generated";
import { mockFetch } from "../test/fetchMock";
import { preview } from "../test/generatedFixtures";
import { ConcludeDialog } from "./ConcludeDialog";

const GET = "GET /api/processes/p1/conclusion";
const POST = "POST /api/processes/p1/conclusion";

const OK: ConclusionResult = { status: "CONCLUIDO", arquivos_removidos: 3, arquivos_pendentes: 0, bytes_liberados: 5_242_880, alertas: [] };

function setup(body: ConclusionPreview = preview(), extra: Parameters<typeof mockFetch>[0] = {}) {
  setCsrfToken("tok");
  const mock = mockFetch({ [GET]: () => ({ status: 200, body }), ...extra });
  const onChanged = vi.fn();
  const onClose = vi.fn();
  render(<ConcludeDialog processId="p1" processVersion={5} onChanged={onChanged} onClose={onClose} />);
  return { ...mock, onChanged, onClose, user: userEvent.setup() };
}

const dialog = () => screen.findByRole("dialog", { name: "Concluir e excluir documentos de entrada" });
const posts = (calls: { method: string; path: string; init?: RequestInit }[]) => calls.filter((c) => `${c.method} ${c.path}` === POST);

describe("DEL-03, UIG-09: a confirmação de ação irreversível", () => {
  it("diz quantos arquivos e quanto espaço serão excluídos de forma irreversível", async () => {
    setup();
    const d = await dialog();
    expect(await within(d).findByText("3 arquivos, 5,0 MB serão excluídos de forma irreversível.")).toBeInTheDocument();
  });

  it("sem documento de entrada informa zero arquivos e zero bytes", async () => {
    setup(preview({ files: 0, bytes: 0 }));
    expect(await screen.findByText("0 arquivos, 0 KB serão excluídos de forma irreversível.")).toBeInTheDocument();
  });

  it("um arquivo fica no singular", async () => {
    setup(preview({ files: 1, bytes: 2048 }));
    expect(await screen.findByText("1 arquivo, 2 KB será excluído de forma irreversível.")).toBeInTheDocument();
  });
});

describe("DEL-01: só conclui com os três documentos gerados", () => {
  it("com um tipo sem versão PRONTO o botão fica desligado e o tipo que falta aparece", async () => {
    setup(preview({ artifacts: { TABELA: true, RELATORIO: true, COMPROVANTE: false } }));
    const d = await dialog();
    expect(await within(d).findByText(/Falta gerar:/)).toHaveTextContent("Comprovante de Documentos");
    expect(within(d).queryByText(/Falta gerar:.*Tabela/)).not.toBeInTheDocument();
    await userEvent.click(within(d).getByLabelText(/Confirmo a exclusão irreversível/));
    expect(within(d).getByRole("button", { name: "Concluir e excluir" })).toBeDisabled();
  });

  it("com os três tipos prontos não mostra a lista do que falta", async () => {
    setup();
    const d = await dialog();
    await within(d).findByText(/serão excluídos/);
    expect(within(d).queryByText(/Falta gerar/)).not.toBeInTheDocument();
  });
});

describe("DEL-04: só envia confirmar: true depois de marcar a confirmação", () => {
  it("o botão fica desligado até marcar e o pedido leva a versão do processo e confirmar true", async () => {
    const { calls, user } = setup(preview(), { [POST]: { status: 200, body: OK } });
    const d = await dialog();
    const button = await within(d).findByRole("button", { name: "Concluir e excluir" });
    expect(button).toBeDisabled();
    await user.click(button);
    expect(posts(calls)).toHaveLength(0);

    await user.click(within(d).getByLabelText(/Confirmo a exclusão irreversível/));
    expect(button).toBeEnabled();
    await user.click(button);
    await waitFor(() => expect(posts(calls)).toHaveLength(1));
    expect(JSON.parse(String(posts(calls)[0].init?.body))).toEqual({ expected_version: 5, confirmar: true });
  });

  it("o sucesso mostra o processo concluído com o que foi excluído e avisa a página", async () => {
    const { onChanged, user } = setup(preview(), { [POST]: { status: 200, body: OK } });
    const d = await dialog();
    await user.click(await within(d).findByLabelText(/Confirmo a exclusão irreversível/));
    await user.click(within(d).getByRole("button", { name: "Concluir e excluir" }));
    expect(await within(d).findByText("Processo concluído.")).toBeInTheDocument();
    expect(within(d).getByText("3 arquivos excluídos, 5,0 MB liberados.")).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalledTimes(1);
    expect(within(d).queryByRole("button", { name: "Concluir e excluir" })).not.toBeInTheDocument();
  });
});

describe("DEL-08: exclusão parcial", () => {
  it("mostra quantos arquivos faltam e permite repetir até concluir", async () => {
    let answers = 0;
    const partial: ConclusionResult = {
      status: "EM_ANDAMENTO",
      arquivos_removidos: 2,
      arquivos_pendentes: 1,
      bytes_liberados: 3_145_728,
      alertas: [{ code: "EXCLUSAO_PARCIAL", message: "1 arquivo ficou" }],
    };
    const { calls, user } = setup(preview(), {
      [POST]: () => ({ status: 200, body: answers++ === 0 ? partial : { ...OK, arquivos_removidos: 1 } }),
    });
    const d = await dialog();
    await user.click(await within(d).findByLabelText(/Confirmo a exclusão irreversível/));
    await user.click(within(d).getByRole("button", { name: "Concluir e excluir" }));

    expect(await within(d).findByRole("alert")).toHaveTextContent("Nem todos os arquivos foram excluídos: tente de novo");
    expect(within(d).getByText("2 arquivos excluídos, 1 arquivo ainda por excluir.")).toBeInTheDocument();
    expect(within(d).queryByText("Processo concluído.")).not.toBeInTheDocument();

    await user.click(within(d).getByRole("button", { name: "Tentar de novo" }));
    expect(await within(d).findByText("Processo concluído.")).toBeInTheDocument();
    expect(posts(calls)).toHaveLength(2);
    expect(JSON.parse(String(posts(calls)[1].init?.body))).toEqual({ expected_version: 5, confirmar: true });
  });
});

describe("DEL-02, DEL-15: recusas do servidor em português", () => {
  async function confirmAndSubmit(response: { status: number; body: unknown }) {
    const ctx = setup(preview(), { [POST]: response });
    const d = await dialog();
    await ctx.user.click(await within(d).findByLabelText(/Confirmo a exclusão irreversível/));
    await ctx.user.click(within(d).getByRole("button", { name: "Concluir e excluir" }));
    return { ...ctx, d };
  }

  it("409 OPERACAO_EM_ANDAMENTO pede para esperar e nada é dado como concluído", async () => {
    const { d, onChanged } = await confirmAndSubmit({ status: 409, body: { detail: "x", code: "OPERACAO_EM_ANDAMENTO" } });
    expect(await within(d).findByRole("alert")).toHaveTextContent("Há geração, redação ou leitura de documento em andamento. Espere terminar.");
    expect(onChanged).not.toHaveBeenCalled();
    expect(within(d).queryByText("Processo concluído.")).not.toBeInTheDocument();
  });

  it("422 ARTEFATOS_PENDENTES mostra a mensagem do servidor, que lista os tipos que faltam", async () => {
    const { d } = await confirmAndSubmit({
      status: 422,
      body: { detail: [{ field: "conclusao", code: "ARTEFATOS_PENDENTES", message: "Faltam versões prontas: COMPROVANTE." }] },
    });
    expect(await within(d).findByRole("alert")).toHaveTextContent("Faltam versões prontas: COMPROVANTE.");
  });

  it("409 VERSAO_DESATUALIZADA avisa e manda a página recarregar o processo", async () => {
    const { d, onChanged } = await confirmAndSubmit({ status: 409, body: { detail: "x", code: "VERSAO_DESATUALIZADA" } });
    expect(await within(d).findByRole("alert")).toHaveTextContent("Os dados mudaram desde que você abriu a tela");
    expect(onChanged).toHaveBeenCalledTimes(1);
  });
});

describe("fechar sem concluir", () => {
  it("Cancelar fecha o diálogo sem enviar nada", async () => {
    const { calls, onClose, user } = setup();
    const d = await dialog();
    await user.click(within(d).getByRole("button", { name: "Cancelar" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(posts(calls)).toHaveLength(0);
  });
});
