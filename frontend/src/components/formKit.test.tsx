import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { Alert, Field, FormProblem, useSubmit } from "./formKit";

function Harness({ action, onChanged }: { action: () => Promise<void>; onChanged: () => void }) {
  const { submit, errors, fileIssues, error, busy } = useSubmit(action, onChanged);
  return (
    <form onSubmit={submit} noValidate aria-label="Formulário de teste">
      <Field id="nome" label="Nome da tabela" error={errors.name}>
        {(p) => <input {...p} />}
      </Field>
      {fileIssues.length > 0 && (
        <ul aria-label="Erros do arquivo">
          {fileIssues.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
      <Alert message={error} />
      <button type="submit" disabled={busy}>
        Enviar
      </button>
    </form>
  );
}

async function send(action: () => Promise<void>) {
  const onChanged = vi.fn();
  render(<Harness action={action} onChanged={onChanged} />);
  await userEvent.setup().click(screen.getByRole("button", { name: "Enviar" }));
  return onChanged;
}

describe("formKit: Field", () => {
  it("liga o rótulo ao campo e, com erro, o marca como inválido e o descreve pela mensagem", () => {
    render(
      <Field id="nome" label="Nome da tabela" error="Já existe uma tabela com este nome">
        {(p) => <input {...p} />}
      </Field>,
    );

    const input = screen.getByLabelText("Nome da tabela");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAttribute("aria-describedby", "nome-error");
    expect(document.getElementById("nome-error")).toHaveTextContent("Já existe uma tabela com este nome");
  });

  it("sem erro o campo não é marcado como inválido nem descrito", () => {
    render(<Field id="nome" label="Nome da tabela">{(p) => <input {...p} />}</Field>);

    const input = screen.getByLabelText("Nome da tabela");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input).not.toHaveAttribute("aria-describedby");
  });
});

describe("formKit: useSubmit", () => {
  it("em caso de sucesso chama onChanged e não mostra erro", async () => {
    const onChanged = await send(async () => undefined);

    expect(onChanged).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("um 422 por campo aparece junto do campo e não chama onChanged", async () => {
    const onChanged = await send(async () => {
      throw new ApiError(422, [{ field: "name", message: "Já existe uma tabela com este nome" }]);
    });

    expect(onChanged).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Nome da tabela")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Já existe uma tabela com este nome")).toBeInTheDocument();
  });

  it("um 422 do campo `file` vira lista à parte, sem marcar nenhum campo", async () => {
    await send(async () => {
      throw new ApiError(422, [
        { field: "file", message: "linha 2, campo pontos: valor inválido" },
        { field: "file", message: "linha 5, campo modo: modo inválido" },
      ]);
    });

    const list = screen.getByRole("list", { name: "Erros do arquivo" });
    expect(within(list).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "linha 2, campo pontos: valor inválido",
      "linha 5, campo modo: modo inválido",
    ]);
    expect(screen.getByLabelText("Nome da tabela")).not.toHaveAttribute("aria-invalid");
  });

  it("um FormProblem vira erro do campo informado", async () => {
    await send(async () => {
      throw new FormProblem("name", "Informe o nome.");
    });

    expect(screen.getByText("Informe o nome.")).toBeInTheDocument();
    expect(screen.getByLabelText("Nome da tabela")).toHaveAttribute("aria-invalid", "true");
  });

  it("outro erro (409) aparece como alerta geral, com a mensagem da API", async () => {
    await send(async () => {
      throw new ApiError(409, "Vigência sobrepõe a versão \"FASI 2022\"");
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Vigência sobrepõe a versão \"FASI 2022\"");
    expect(screen.getByLabelText("Nome da tabela")).not.toHaveAttribute("aria-invalid");
  });
});
