import { useState, type ChangeEvent } from "react";
import {
  BOARD_ROLES,
  rereadOrdinance,
  saveOrdinance,
  uploadOrdinance,
  type BoardMember,
  type BoardRole,
  type Ordinance,
  type OrdinanceWarningCode,
  type ValueSource,
} from "../api/board";
import { boardFailure } from "../boardErrors";
import {
  BOARD_ROLE_LABELS,
  ORDINANCE_WARNING_LABELS,
  READING_CODE_LABELS,
  READING_STATE_LABELS,
  VALUE_SOURCE_LABELS,
  formatSize,
} from "../labels";
import { FieldError } from "./FieldError";
import { Modal } from "./Modal";

type Row = { key: number; name: string; role: BoardRole; origin: BoardMember | null };

let nextRowKey = 0;
const rowsOf = (ordinance: Ordinance): Row[] =>
  ordinance.members.map((member) => ({ key: nextRowKey++, name: member.name, role: member.role, origin: member }));

/** PORT-02, PORT-05: where a value came from; a value the person typed has no page. */
function originText(source: ValueSource | null, page: number | null): string | null {
  if (source === "INFORMADO") return VALUE_SOURCE_LABELS.INFORMADO;
  if (source === "EXTRAIDO") {
    return page === null ? VALUE_SOURCE_LABELS.EXTRAIDO : `${VALUE_SOURCE_LABELS.EXTRAIDO}, página ${page}`;
  }
  return null;
}

const fieldProps = (field: string, errors: Record<string, string>, warned: boolean) => {
  const described = [warned ? `ordinance-${field}-warning` : null, errors[field] ? `ordinance-${field}-error` : null].filter(Boolean);
  return {
    id: `ordinance-${field}`,
    "aria-invalid": errors[field] ? (true as const) : undefined,
    "aria-describedby": described.length > 0 ? described.join(" ") : undefined,
  };
};

/**
 * PORT-01..08, PORT-10..12, BNAV-02: the ordinance of the board. The person sends the file, checks
 * the number, the date and the members the system read (each with its page, or "informado pela
 * pessoa" once typed) and saves them; without a file the same fields are typed by hand.
 *
 * The form is controlled by the page: `ordinance` is what the server last sent, `onChanged` receives
 * what a call returned and `onStale` asks the page to read the board again after a 409. The fields
 * start again from the ordinance whenever the server sends a new version, state or reason, and stay
 * locked while a reading is queued or running, so the reading never overwrites what is being typed.
 */
export function OrdinanceForm({
  processId,
  ordinance,
  readOnly = false,
  readOnlyReason,
  onChanged,
  onStale,
}: {
  processId: string;
  ordinance: Ordinance;
  readOnly?: boolean;
  readOnlyReason?: string;
  onChanged: (next: Ordinance) => void;
  onStale?: () => void;
}) {
  const [number, setNumber] = useState(ordinance.number ?? "");
  const [date, setDate] = useState(ordinance.ordinance_date ?? "");
  const [rows, setRows] = useState<Row[]>(() => rowsOf(ordinance));
  const syncKey = `${ordinance.version}|${ordinance.reading_state}|${ordinance.reading_code}`;
  const [seen, setSeen] = useState(syncKey);
  if (seen !== syncKey) {
    setSeen(syncKey);
    setNumber(ordinance.number ?? "");
    setDate(ordinance.ordinance_date ?? "");
    setRows(rowsOf(ordinance));
  }

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const state = ordinance.reading_state;
  const reading = state === "PENDENTE" || state === "LENDO";
  const locked = readOnly || reading || busy;
  const file = ordinance.file;
  const hasStoredFile = file !== null && !file.deleted;

  const warned = (field: string, code: OrdinanceWarningCode) => ordinance.warnings.some((w) => w.field === field && w.code === code);
  const memberCodes = [...new Set(ordinance.warnings.filter((w) => w.field === "members").map((w) => w.code))];

  async function run(action: () => Promise<Ordinance>) {
    setErrors({});
    setMessage(null);
    setBusy(true);
    try {
      onChanged(await action());
    } catch (err) {
      const failure = boardFailure(err);
      setErrors(failure.fields);
      setMessage(failure.message);
      if (failure.stale) onStale?.();
    } finally {
      setBusy(false);
    }
  }

  function choose(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0];
    event.target.value = "";
    if (!chosen) return;
    if (hasStoredFile) setPendingFile(chosen);
    else void run(() => uploadOrdinance(processId, chosen, ordinance.version, false));
  }

  function replace() {
    const chosen = pendingFile;
    setPendingFile(null);
    if (chosen) void run(() => uploadOrdinance(processId, chosen, ordinance.version, true));
  }

  function save() {
    void run(() =>
      saveOrdinance(processId, {
        number: number.trim() || null,
        ordinance_date: date || null,
        members: rows.map((row) => ({ name: row.name.trim(), role: row.role })),
        expected_version: ordinance.version,
      }),
    );
  }

  const edit = (key: number, change: Partial<Pick<Row, "name" | "role">>) =>
    setRows((all) => all.map((row) => (row.key === key ? { ...row, ...change } : row)));

  const numberOrigin = number === (ordinance.number ?? "") ? originText(ordinance.number_source, ordinance.number_page) : null;
  const dateOrigin = date === (ordinance.ordinance_date ?? "") ? originText(ordinance.date_source, ordinance.date_page) : null;

  return (
    <div className="ordinance-form">
      {readOnlyReason && readOnly && <p className="muted">{readOnlyReason}</p>}

      <div className="field">
        <label htmlFor="ordinance-arquivo">Arquivo da portaria</label>
        <input
          {...fieldProps("arquivo", errors, false)}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
          disabled={locked}
          onChange={choose}
        />
        <small className="muted">PDF, PNG ou JPEG de até 20 MB.</small>
        <FieldError id="ordinance-arquivo-error" message={errors.arquivo} />
        {hasStoredFile && (
          <p>
            <a href={`/api/processes/${processId}/board/ordinance/file`} target="_blank" rel="noreferrer">
              {`Ver o arquivo enviado: ${file.original_name} (${formatSize(file.size_bytes)})`}
            </a>
          </p>
        )}
        {file?.deleted && <p className="muted">O arquivo foi excluído na conclusão do processo; os dados da portaria ficam.</p>}
      </div>

      {state === "FALHOU" ? (
        <div role="alert" className="error">
          <p>
            {`${READING_STATE_LABELS.FALHOU}${ordinance.reading_code ? `: ${READING_CODE_LABELS[ordinance.reading_code]}` : "."}`}
          </p>
          <button type="button" className="btn btn-secondary" disabled={readOnly || busy} onClick={() => void run(() => rereadOrdinance(processId, ordinance.version))}>
            Ler de novo
          </button>
        </div>
      ) : (
        state !== "SEM_ARQUIVO" && <p role="status">{READING_STATE_LABELS[state]}</p>
      )}

      <div className="field">
        <label htmlFor="ordinance-number">Número da portaria</label>
        <input
          {...fieldProps("number", errors, warned("number", "VALOR_SEM_ORIGEM"))}
          type="text"
          value={number}
          disabled={locked}
          onChange={(event) => setNumber(event.target.value)}
        />
        {numberOrigin && (
          <small className="muted" data-testid="origin-number">
            {numberOrigin}
          </small>
        )}
        {warned("number", "VALOR_SEM_ORIGEM") && (
          <p id="ordinance-number-warning" className="doc-warning sev-ALERTA">
            {ORDINANCE_WARNING_LABELS.VALOR_SEM_ORIGEM}
          </p>
        )}
        <FieldError id="ordinance-number-error" message={errors.number} />
      </div>

      <div className="field">
        <label htmlFor="ordinance-ordinance_date">Data da portaria</label>
        <input
          {...fieldProps("ordinance_date", errors, warned("ordinance_date", "VALOR_SEM_ORIGEM"))}
          type="date"
          value={date}
          disabled={locked}
          onChange={(event) => setDate(event.target.value)}
        />
        {dateOrigin && (
          <small className="muted" data-testid="origin-ordinance_date">
            {dateOrigin}
          </small>
        )}
        {warned("ordinance_date", "VALOR_SEM_ORIGEM") && (
          <p id="ordinance-ordinance_date-warning" className="doc-warning sev-ALERTA">
            {ORDINANCE_WARNING_LABELS.VALOR_SEM_ORIGEM}
          </p>
        )}
        <FieldError id="ordinance-ordinance_date-error" message={errors.ordinance_date} />
      </div>

      <fieldset>
        <legend>Membros da banca</legend>
        {memberCodes.map((code) => (
          <p key={code} className="doc-warning sev-ALERTA">
            {ORDINANCE_WARNING_LABELS[code]}
          </p>
        ))}
        <ul className="board-members">
          {rows.map((row, index) => {
            const field = `members[${index}].name`;
            const origin = row.origin && row.origin.name === row.name && row.origin.role === row.role ? originText(row.origin.source, row.origin.page) : null;
            return (
              <li key={row.key}>
                <input
                  {...fieldProps(field, errors, false)}
                  type="text"
                  aria-label={`Nome do membro ${index + 1}`}
                  value={row.name}
                  disabled={locked}
                  onChange={(event) => edit(row.key, { name: event.target.value })}
                />
                <select
                  aria-label={`Função do membro ${index + 1}`}
                  value={row.role}
                  disabled={locked}
                  onChange={(event) => edit(row.key, { role: event.target.value as BoardRole })}
                >
                  {BOARD_ROLES.map((role) => (
                    <option key={role} value={role}>
                      {BOARD_ROLE_LABELS[role]}
                    </option>
                  ))}
                </select>
                {origin && <small className="muted">{origin}</small>}
                <button
                  type="button"
                  className="btn btn-secondary"
                  aria-label={`Remover membro ${index + 1}`}
                  disabled={locked}
                  onClick={() => setRows((all) => all.filter((r) => r.key !== row.key))}
                >
                  Remover
                </button>
                <FieldError id={`ordinance-${field}-error`} message={errors[field]} />
              </li>
            );
          })}
        </ul>
        <FieldError id="ordinance-members-error" message={errors.members} />
        <button
          type="button"
          className="btn btn-secondary"
          disabled={locked}
          onClick={() => setRows((all) => [...all, { key: nextRowKey++, name: "", role: "MEMBRO", origin: null }])}
        >
          Adicionar membro
        </button>
      </fieldset>

      {message && (
        <p role="alert" className="error">
          {message}
        </p>
      )}
      <div className="btn-row">
        <button type="button" className="btn btn-primary" disabled={locked} onClick={save}>
          Salvar dados da portaria
        </button>
      </div>

      {pendingFile && (
        <Modal title="Substituir a portaria" onClose={() => setPendingFile(null)}>
          <p>O arquivo enviado antes sai do servidor e o novo é lido. O que você digitou e salvou não é sobrescrito pela leitura.</p>
          <div className="btn-row">
            <button type="button" className="btn btn-primary" onClick={replace}>
              Substituir
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setPendingFile(null)}>
              Cancelar
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
