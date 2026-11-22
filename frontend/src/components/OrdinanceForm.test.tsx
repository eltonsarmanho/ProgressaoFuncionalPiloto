import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { Ordinance } from "../api/board";
import { emptyOrdinance, ordinance } from "../test/boardFixtures";
import { mockFetch, type MockResponse } from "../test/fetchMock";
import { OrdinanceForm } from "./OrdinanceForm";

const FILE_PATH = "PUT /api/processes/p1/board/ordinance/file";
const DATA_PATH = "PUT /api/processes/p1/board/ordinance";
const REREAD_PATH = "POST /api/processes/p1/board/ordinance/reread";
const STALE_TEXT = "Os dados foram alterados por outra pessoa; recarregue";

/** Holds the ordinance as the page does: the form is controlled and the page keeps what the server sent. */
function Harness({ initial, onSeen, ...rest }: { initial: Ordinance; onSeen?: (o: Ordinance) => void; readOnly?: boolean; readOnlyReason?: string; onStale?: () => void }) {
  const [current, setCurrent] = useState(initial);
  return (
    <OrdinanceForm
      processId="p1"
      ordinance={current}
      onChanged={(next) => {
        setCurrent(next);
        onSeen?.(next);
      }}
      {...rest}
    />
  );
}

const pdf = () => new File(["%PDF-1.4"], "nova.pdf", { type: "application/pdf" });
const save = () => screen.getByRole("button", { name: "Salvar dados da portaria" });
const rowOf = (name: string) => screen.getByDisplayValue(name).closest("li") as HTMLElement;

describe("PORT-01, PORT-06: sem portaria", () => {
  it("mostra o envio e os campos vazios, sem estado de leitura nem 'Ler de novo'", () => {
    render(<Harness initial={emptyOrdinance()} />);
    expect(screen.getByLabelText("Arquivo da portaria")).toBeEnabled();
    expect(screen.getByLabelText("Número da portaria")).toHaveValue("");
    expect(screen.getByLabelText("Data da portaria")).toHaveValue("");
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Ler de novo" })).not.toBeInTheDocument();
    expect(screen.queryByText("Sem arquivo")).not.toBeInTheDocument();
  });

  it("PORT-01: escolher um PDF envia FormData com o arquivo e expected_version 0, sem substituição", async () => {
    const sent = ordinance({ reading_state: "PENDENTE", number: null, number_page: null, number_source: null, members: [], version: 1 });
    const { calls } = mockFetch({ [FILE_PATH]: { status: 200, body: sent } });
    const seen = vi.fn();
    render(<Harness initial={emptyOrdinance()} onSeen={seen} />);
    const file = pdf();
    await userEvent.upload(screen.getByLabelText("Arquivo da portaria"), file);
    await waitFor(() => expect(calls).toHaveLength(1));
    const form = calls[0].init!.body as FormData;
    expect(form.get("file")).toBe(file);
    expect(form.get("expected_version")).toBe("0");
    expect(form.get("replace")).toBe("false");
    await waitFor(() => expect(seen).toHaveBeenCalledWith(sent));
    expect(await screen.findByText("Na fila de leitura")).toBeInTheDocument();
  });

  it("PORT-06: salvar os dados sem arquivo envia a versão 0 e mostra todos como 'informado pela pessoa'", async () => {
    const typed = ordinance({
      file: null,
      reading_state: "SEM_ARQUIVO",
      number: "7/2026",
      number_page: null,
      number_source: "INFORMADO",
      ordinance_date: "2026-09-01",
      date_page: null,
      date_source: "INFORMADO",
      members: [{ name: "Ana Sintética", role: "PRESIDENTE", page: null, source: "INFORMADO" }],
      version: 1,
    });
    const { calls } = mockFetch({ [DATA_PATH]: { status: 200, body: typed } });
    render(<Harness initial={emptyOrdinance()} />);
    await userEvent.type(screen.getByLabelText("Número da portaria"), "7/2026");
    await userEvent.type(screen.getByLabelText("Data da portaria"), "2026-09-01");
    await userEvent.click(screen.getByRole("button", { name: "Adicionar membro" }));
    await userEvent.type(screen.getByLabelText("Nome do membro 1"), "Ana Sintética");
    await userEvent.selectOptions(screen.getByLabelText("Função do membro 1"), "PRESIDENTE");
    await userEvent.click(save());
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({
      number: "7/2026",
      ordinance_date: "2026-09-01",
      members: [{ name: "Ana Sintética", role: "PRESIDENTE" }],
      expected_version: 0,
    });
    await waitFor(() => expect(screen.getAllByText("informado pela pessoa")).toHaveLength(3));
    expect(screen.queryByText(/página/)).not.toBeInTheDocument();
  });
});

describe("PORT-02, PORT-03: portaria lida", () => {
  it("mostra os três membros com 'página 2' e o número e a data com a sua página", () => {
    render(<Harness initial={ordinance()} />);
    expect(screen.getByText("Portaria lida")).toBeInTheDocument();
    expect(screen.getByLabelText("Número da portaria")).toHaveValue("123/2026");
    expect(screen.getByLabelText("Data da portaria")).toHaveValue("2026-10-05");
    expect(screen.getByTestId("origin-number")).toHaveTextContent("página 1");
    expect(screen.getByTestId("origin-ordinance_date")).toHaveTextContent("página 1");
    for (const name of ["Ana Sintética", "Bruno Fictício", "Carla Exemplo"]) {
      expect(within(rowOf(name)).getByText(/página 2/)).toBeInTheDocument();
    }
    expect(within(rowOf("Ana Sintética")).getByLabelText("Função do membro 1")).toHaveValue("PRESIDENTE");
    expect(within(rowOf("Carla Exemplo")).getByLabelText("Função do membro 3")).toHaveValue("SUPLENTE");
    expect(screen.getByRole("link", { name: /portaria-sintetica\.pdf/ })).toHaveAttribute("href", "/api/processes/p1/board/ordinance/file");
  });

  it("PORT-03: valor sem origem mostra o aviso no campo e o campo vazio", () => {
    render(
      <Harness
        initial={ordinance({
          number: null,
          number_page: null,
          number_source: null,
          warnings: [{ code: "VALOR_SEM_ORIGEM", field: "number" }],
        })}
      />,
    );
    expect(screen.getByLabelText("Número da portaria")).toHaveValue("");
    expect(screen.getByLabelText("Número da portaria")).toHaveAccessibleDescription(
      "O valor não aparece no texto da página citada: confira e digite",
    );
    expect(screen.getByLabelText("Data da portaria")).not.toHaveAccessibleDescription(/não aparece/);
  });

  it("PORT-03: o aviso de membro sem origem aparece na lista de membros, uma vez só", () => {
    render(
      <Harness
        initial={ordinance({
          warnings: [
            { code: "VALOR_SEM_ORIGEM", field: "members" },
            { code: "VALOR_SEM_ORIGEM", field: "members" },
          ],
        })}
      />,
    );
    expect(screen.getAllByText("O valor não aparece no texto da página citada: confira e digite")).toHaveLength(1);
  });

  it("MEMBROS_NAO_ENCONTRADOS mostra o aviso e deixa digitar os membros", async () => {
    render(<Harness initial={ordinance({ members: [], warnings: [{ code: "MEMBROS_NAO_ENCONTRADOS", field: "members" }] })} />);
    expect(screen.getByText("Nenhum membro foi encontrado na portaria: digite os membros")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Adicionar membro" }));
    expect(screen.getByLabelText("Nome do membro 1")).toBeEnabled();
  });
});

describe("PORT-05: conferir e corrigir", () => {
  it("corrigir um nome e salvar envia a lista e marca só esse membro como 'informado pela pessoa'", async () => {
    const after = ordinance({
      members: [
        { name: "Ana Sintética", role: "PRESIDENTE", page: 2, source: "EXTRAIDO" },
        { name: "Bruno Corrigido", role: "MEMBRO", page: null, source: "INFORMADO" },
        { name: "Carla Exemplo", role: "SUPLENTE", page: 2, source: "EXTRAIDO" },
      ],
      version: 4,
    });
    const { calls } = mockFetch({ [DATA_PATH]: { status: 200, body: after } });
    render(<Harness initial={ordinance()} />);
    const name = screen.getByLabelText("Nome do membro 2");
    await userEvent.clear(name);
    await userEvent.type(name, "Bruno Corrigido");
    await userEvent.click(save());
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({
      number: "123/2026",
      ordinance_date: "2026-10-05",
      members: [
        { name: "Ana Sintética", role: "PRESIDENTE" },
        { name: "Bruno Corrigido", role: "MEMBRO" },
        { name: "Carla Exemplo", role: "SUPLENTE" },
      ],
      expected_version: 3,
    });
    await waitFor(() => expect(within(rowOf("Bruno Corrigido")).getByText("informado pela pessoa")).toBeInTheDocument());
    expect(within(rowOf("Ana Sintética")).queryByText("informado pela pessoa")).not.toBeInTheDocument();
    expect(within(rowOf("Ana Sintética")).getByText(/página 2/)).toBeInTheDocument();
  });

  it("adiciona e remove membros: a lista enviada é a que está na tela", async () => {
    const { calls } = mockFetch({ [DATA_PATH]: { status: 200, body: ordinance({ version: 4 }) } });
    render(<Harness initial={ordinance()} />);
    await userEvent.click(screen.getByRole("button", { name: "Remover membro 1" }));
    expect(screen.queryByDisplayValue("Ana Sintética")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Adicionar membro" }));
    await userEvent.type(screen.getByLabelText("Nome do membro 3"), "Davi Novo");
    await userEvent.selectOptions(screen.getByLabelText("Função do membro 3"), "SUPLENTE");
    await userEvent.click(save());
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(JSON.parse(calls[0].init!.body as string).members).toEqual([
      { name: "Bruno Fictício", role: "MEMBRO" },
      { name: "Carla Exemplo", role: "SUPLENTE" },
      { name: "Davi Novo", role: "SUPLENTE" },
    ]);
  });
});

describe("PORT-07: leitura que falha", () => {
  const failed = () => ordinance({ reading_state: "FALHOU", reading_code: "TEXTO_ILEGIVEL", number: null, members: [] });

  it("mostra o motivo em português, mantém os campos editáveis e 'Ler de novo' chama a nova leitura", async () => {
    const queued = failed();
    queued.reading_state = "PENDENTE";
    queued.reading_code = null;
    const { calls } = mockFetch({ [REREAD_PATH]: { status: 200, body: queued } });
    render(<Harness initial={failed()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("A leitura falhou");
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível ler o texto do arquivo.");
    expect(screen.getByLabelText("Número da portaria")).toBeEnabled();
    expect(screen.getByLabelText("Data da portaria")).toBeEnabled();
    expect(screen.getByRole("button", { name: "Adicionar membro" })).toBeEnabled();
    expect(save()).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: "Ler de novo" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({ expected_version: 3 });
    expect(await screen.findByText("Na fila de leitura")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ler de novo" })).not.toBeInTheDocument();
  });
});

describe("PORT-08: substituição", () => {
  it("enviar outro arquivo abre a confirmação e só envia replace verdadeiro depois de confirmar", async () => {
    const { calls } = mockFetch({ [FILE_PATH]: { status: 200, body: ordinance({ reading_state: "PENDENTE", version: 4 }) } });
    render(<Harness initial={ordinance()} />);
    await userEvent.upload(screen.getByLabelText("Arquivo da portaria"), pdf());
    const dialog = await screen.findByRole("dialog", { name: "Substituir a portaria" });
    expect(calls).toHaveLength(0);
    await userEvent.click(within(dialog).getByRole("button", { name: "Substituir" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    const form = calls[0].init!.body as FormData;
    expect(form.get("replace")).toBe("true");
    expect(form.get("expected_version")).toBe("3");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("cancelar a confirmação não envia nada", async () => {
    const { calls } = mockFetch({});
    render(<Harness initial={ordinance()} />);
    await userEvent.upload(screen.getByLabelText("Arquivo da portaria"), pdf());
    const dialog = await screen.findByRole("dialog", { name: "Substituir a portaria" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });
});

describe("PORT-10, PORT-11, PORT-12: recusas", () => {
  it("PORT-11: 422 no members[1].name mostra o erro junto do nome", async () => {
    mockFetch({
      [DATA_PATH]: { status: 422, body: { detail: [{ field: "members[1].name", message: "Nome do membro é obrigatório" }] } },
    });
    render(<Harness initial={ordinance()} />);
    await userEvent.clear(screen.getByLabelText("Nome do membro 2"));
    await userEvent.click(save());
    const error = await screen.findByText("Nome do membro é obrigatório");
    expect(within(rowOf("Ana Sintética")).queryByText("Nome do membro é obrigatório")).not.toBeInTheDocument();
    expect(error.closest("li")).toBe(screen.getByLabelText("Nome do membro 2").closest("li"));
    expect(screen.getByLabelText("Nome do membro 2")).toBeInvalid();
  });

  it("PORT-11: 422 no número mostra o erro junto do campo", async () => {
    mockFetch({ [DATA_PATH]: { status: 422, body: { detail: [{ field: "number", message: "Número deve ter até 50 caracteres" }] } } });
    render(<Harness initial={ordinance()} />);
    await userEvent.click(save());
    expect(await screen.findByLabelText("Número da portaria")).toHaveAccessibleDescription(/Número deve ter até 50 caracteres/);
  });

  it("PORT-10: 422 do arquivo mostra a mensagem do limite junto do envio", async () => {
    mockFetch({
      [FILE_PATH]: { status: 422, body: { detail: [{ field: "arquivo", code: "ARQUIVO_GRANDE", message: "O arquivo passa do tamanho máximo." }] } },
    });
    render(<Harness initial={emptyOrdinance()} />);
    await userEvent.upload(screen.getByLabelText("Arquivo da portaria"), pdf());
    expect(await screen.findByLabelText("Arquivo da portaria")).toHaveAccessibleDescription("O arquivo passa do tamanho máximo.");
  });

  it("PORT-12: 409 VERSAO_DESATUALIZADA mostra o texto de recarregar e avisa a página", async () => {
    const stale: MockResponse = { status: 409, body: { detail: "A portaria foi alterada por outro usuário; recarregue", code: "VERSAO_DESATUALIZADA" } };
    mockFetch({ [DATA_PATH]: stale });
    const onStale = vi.fn();
    render(<Harness initial={ordinance()} onStale={onStale} />);
    await userEvent.click(save());
    expect(await screen.findByRole("alert")).toHaveTextContent(STALE_TEXT);
    expect(onStale).toHaveBeenCalledTimes(1);
  });
});

describe("BNAV-02: somente leitura", () => {
  it("desabilita o envio, os campos, 'Ler de novo' e o salvar, com o motivo", () => {
    const reason = "O processo está concluído ou arquivado e não aceita alterações.";
    render(
      <Harness
        initial={ordinance({ reading_state: "FALHOU", reading_code: "IA_INDISPONIVEL" })}
        readOnly
        readOnlyReason={reason}
      />,
    );
    expect(screen.getByText(reason)).toBeInTheDocument();
    expect(screen.getByLabelText("Arquivo da portaria")).toBeDisabled();
    expect(screen.getByLabelText("Número da portaria")).toBeDisabled();
    expect(screen.getByLabelText("Data da portaria")).toBeDisabled();
    expect(screen.getByLabelText("Nome do membro 1")).toBeDisabled();
    expect(screen.getByLabelText("Função do membro 1")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Remover membro 1" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Adicionar membro" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Ler de novo" })).toBeDisabled();
    expect(save()).toBeDisabled();
  });

  it("o arquivo excluído na conclusão é dito na tela e os dados ficam", () => {
    render(
      <Harness
        initial={ordinance({ file: { original_name: "portaria-sintetica.pdf", mime: "application/pdf", size_bytes: 2048, page_count: 2, deleted: true } })}
        readOnly
        readOnlyReason="Processo concluído."
      />,
    );
    expect(screen.getByText(/arquivo foi excluído/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /portaria-sintetica/ })).not.toBeInTheDocument();
    expect(screen.getByDisplayValue("Ana Sintética")).toBeInTheDocument();
  });
});
