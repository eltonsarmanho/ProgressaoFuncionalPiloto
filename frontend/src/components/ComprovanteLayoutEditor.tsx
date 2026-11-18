import { useEffect, useState, type FormEvent } from "react";
import { request } from "../api/client";
import type { GenerationAlert, LayoutActivity, LayoutPage, LayoutView, PageRef, Staleness, TocEntry } from "../api/generated";
import type { DocumentSummary } from "../api/types";
import { generationErrorMessage, isConflict } from "../generationErrors";
import { GENERATION_CODE_LABELS, alertText, itemLabel, roman } from "../labels";
import { Modal } from "./Modal";

const pageKey = (documentId: string, page: number) => `${documentId}:${page}`;

/** What changed in the activities since the arrangement was saved, in a short line (ARR-08). */
function stalenessLine(s: Staleness): string {
  const part = (n: number, one: string, many: string) => (n === 0 ? [] : [n === 1 ? `1 ${one}` : `${n} ${many}`]);
  return [
    ...part(s.left_activity_ids.length, "saiu", `saíram`),
    ...part(s.moved_activity_ids.length, "mudou de item", "mudaram de item"),
    ...part(s.new_link_activity_ids.length, "tem vínculo novo", "têm vínculo novo"),
    ...part(s.joined_activity_ids.length, "entrou", "entraram"),
  ].join(" · ");
}

/** CMP-06: the justification the user gives to attach a page again in an activity. */
function RepeatDialog({ onSave, onCancel }: { onSave: (justification: string) => void; onCancel: () => void }) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) {
      setError("Informe a justificativa da repetição.");
      return;
    }
    onSave(text.trim());
  }

  return (
    <Modal title="Repetir página" onClose={onCancel}>
      <p className="muted">
        A página já está em outra atividade; por padrão ela é anexada uma só vez e as demais citam o número. Repetir
        anexa a página de novo e guarda a justificativa no arranjo.
      </p>
      <form onSubmit={submit} noValidate>
        <label htmlFor="repeat-justification">Justificativa da repetição</label>
        <textarea
          id="repeat-justification"
          rows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-invalid={error ? true : undefined}
        />
        {error && (
          <p role="alert" className="error field-error">
            {error}
          </p>
        )}
        <div className="btn-row">
          <button type="submit" className="btn btn-primary">
            Repetir página
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** ARR-02: a page of a document of the process, at a position of the activity. */
function AddPageForm({
  title,
  count,
  documents,
  onAdd,
  onCancel,
}: {
  title: string;
  count: number;
  documents: DocumentSummary[];
  onAdd: (page: LayoutPage, position: number) => void;
  onCancel: () => void;
}) {
  const [documentId, setDocumentId] = useState("");
  const [page, setPage] = useState("1");
  const [position, setPosition] = useState("");
  const [error, setError] = useState<string | null>(null);
  const idBase = `add-${title.replace(/\s+/g, "-")}`;

  function submit(event: FormEvent) {
    event.preventDefault();
    const doc = documents.find((d) => d.id === documentId);
    const number = Number(page);
    if (!doc) return setError("Escolha o documento.");
    if (!Number.isInteger(number) || number < 1) return setError("Informe a página.");
    if (number > doc.page_count) return setError(GENERATION_CODE_LABELS.PAGINA_FORA_DO_DOCUMENTO);
    const at = Number.parseInt(position, 10);
    const where = Number.isNaN(at) ? count + 1 : Math.min(Math.max(at, 1), count + 1);
    onAdd({ document_id: doc.id, page: number, repeat_justification: null }, where);
  }

  return (
    <form onSubmit={submit} noValidate>
      <fieldset className="grid">
        <legend className="visually-hidden">{`Acrescentar página em ${title}`}</legend>
        <div>
          <label htmlFor={`${idBase}-doc`}>Documento</label>
          <select id={`${idBase}-doc`} value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
            <option value="">Escolha o documento</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {`${d.original_name} (${d.page_count} ${d.page_count === 1 ? "página" : "páginas"})`}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${idBase}-page`}>Página</label>
          <input id={`${idBase}-page`} type="number" min={1} value={page} onChange={(e) => setPage(e.target.value)} />
        </div>
        <div>
          <label htmlFor={`${idBase}-pos`}>Posição</label>
          <input
            id={`${idBase}-pos`}
            type="number"
            min={1}
            max={count + 1}
            placeholder={`${count + 1}`}
            value={position}
            onChange={(e) => setPosition(e.target.value)}
          />
        </div>
        {error && (
          <p role="alert" className="error field-error">
            {error}
          </p>
        )}
        <div className="btn-row">
          <button type="submit" className="btn btn-primary">
            Acrescentar
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancelar
          </button>
        </div>
      </fieldset>
    </form>
  );
}

/** The page a layout entry is in the planned Comprovante, found by its document and page (the nth repeat of it). */
function plannedPage(toc: TocEntry | undefined, activity: LayoutActivity, index: number): PageRef | undefined {
  const page = activity.pages[index];
  const before = activity.pages.slice(0, index).filter((p) => p.document_id === page.document_id && p.page === page.page).length;
  return toc?.sources.filter((s) => s.document_id === page.document_id && s.source_page === page.page)[before];
}

function swap<T>(list: T[], a: number, b: number): T[] {
  const next = [...list];
  [next[a], next[b]] = [next[b], next[a]];
  return next;
}

/**
 * UIG-03, ARR-03, ARR-04: the arrangement of the Comprovante by group, item and activity. The user
 * moves pages and activities up and down and removes pages (keyboard buttons, no drag and drop);
 * nothing is sent until "Salvar arranjo", which sends every activity with the version the server
 * gave. The numbering shown is the server's plan for the saved arrangement. A 409 reloads the
 * arrangement and drops the local changes; an activity never changes its item here (ARR-05).
 */
export function ComprovanteLayoutEditor({ processId, readOnly = false }: { processId: string; readOnly?: boolean }) {
  const [view, setView] = useState<LayoutView | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [draft, setDraft] = useState<LayoutActivity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reloads, setReloads] = useState(0);
  const [adding, setAdding] = useState<string | null>(null);
  const [repeating, setRepeating] = useState<{ index: number; page: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    request<LayoutView>("GET", `/api/processes/${processId}/comprovante-layout`)
      .then((found) => {
        if (cancelled) return;
        setView(found);
        setDraft(null);
      })
      .catch((err) => {
        if (!cancelled) setError(generationErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [processId, reloads]);

  useEffect(() => {
    let cancelled = false;
    request<DocumentSummary[]>("GET", `/api/processes/${processId}/documents`)
      .then((found) => {
        if (!cancelled) setDocuments(found);
      })
      .catch(() => {
        if (!cancelled) setDocuments([]);
      });
    return () => {
      cancelled = true;
    };
  }, [processId]);

  if (!view) {
    return error ? (
      <p role="alert" className="error">
        {error}
      </p>
    ) : (
      <p>Carregando o arranjo…</p>
    );
  }

  const activities = draft ?? view.layout.activities;
  const dirty = draft !== null;
  const tocOf = (id: string) => view.plan.toc.find((e) => e.level === "ATIVIDADE" && e.activity_id === id);
  const docName = (id: string) => documents.find((d) => d.id === id)?.original_name ?? "Documento";
  const groups = [...new Set(activities.map((a) => a.group_number ?? 0))].sort((a, b) => a - b);

  // the first holder of a page, in the order of the table, owns it; the others cite it (CMP-05)
  const owners = new Map<string, number>();
  activities
    .map((a, index) => ({ a, index }))
    .sort((x, y) => (x.a.group_number ?? 0) - (y.a.group_number ?? 0) || (x.a.item_number ?? 0) - (y.a.item_number ?? 0) || x.index - y.index)
    .forEach(({ a, index }) =>
      a.pages.forEach((p) => {
        if (!owners.has(pageKey(p.document_id, p.page))) owners.set(pageKey(p.document_id, p.page), index);
      }),
    );
  const invalid = new Set(view.invalid.map((k) => `${k.activity_id}:${pageKey(k.document_id, k.page)}`));
  const warnings: GenerationAlert[] =
    view.stale && !view.alerts.some((a) => a.code === "ARRANJO_DESATUALIZADO")
      ? [{ code: "ARRANJO_DESATUALIZADO", message: "" }, ...view.alerts]
      : view.alerts;

  const edit = (change: (list: LayoutActivity[]) => LayoutActivity[]) => setDraft(change(activities));
  const editPages = (index: number, change: (pages: LayoutActivity["pages"]) => LayoutActivity["pages"]) =>
    edit((list) => list.map((a, i) => (i === index ? { ...a, pages: change(a.pages) } : a)));

  /** The neighbour of an activity inside its item, in the order of the list. */
  function neighbour(index: number, step: 1 | -1): number | undefined {
    const here = activities[index];
    for (let i = index + step; i >= 0 && i < activities.length; i += step) {
      if (activities[i].group_number === here.group_number && activities[i].item_number === here.item_number) return i;
    }
    return undefined;
  }

  async function save() {
    setError(null);
    setBusy(true);
    try {
      const saved = await request<LayoutView>("PUT", `/api/processes/${processId}/comprovante-layout`, {
        expected_version: view!.layout.version,
        activities: activities.map((a) => ({
          activity_id: a.activity_id,
          pages: a.pages.map((p) => ({
            document_id: p.document_id,
            page: p.page,
            repeat_justification: p.repeat_justification,
          })),
          group_number: a.group_number,
          item_number: a.item_number,
        })),
      });
      setView(saved);
      setDraft(null);
    } catch (err) {
      setError(generationErrorMessage(err));
      if (isConflict(err)) setReloads((n) => n + 1);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="layout-editor">
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {warnings.map((alert) => (
        <p key={alert.code} className="doc-warning sev-ALERTA">
          {alertText(alert)}
        </p>
      ))}
      {view.stale && stalenessLine(view.staleness) && <p className="muted">{stalenessLine(view.staleness)}</p>}
      {!readOnly && dirty && (
        <p className="review-summary">
          Alterações não salvas. A numeração aparece depois de salvar.
        </p>
      )}
      {!readOnly && (
        <div className="btn-row">
          <button type="button" className="btn btn-primary" disabled={!dirty || busy} onClick={() => void save()}>
            Salvar arranjo
          </button>
          {dirty && (
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => setDraft(null)}>
              Descartar alterações
            </button>
          )}
        </div>
      )}
      {groups.map((group) => {
        const inGroup = activities.map((a, index) => ({ a, index })).filter(({ a }) => (a.group_number ?? 0) === group);
        const items = [...new Set(inGroup.map(({ a }) => a.item_number ?? 0))].sort((x, y) => x - y);
        const groupTitle = view.plan.toc.find((e) => e.level === "GRUPO" && e.group_number === group)?.title;
        const headingId = `layout-group-${group}`;
        return (
          <section key={group} className="card layout-group" aria-labelledby={headingId}>
            <h3 id={headingId}>
              {group === 0 ? "Sem enquadramento" : `Grupo ${roman(group)}`}
              {groupTitle && (
                <>
                  {" · "}
                  <span>{groupTitle}</span>
                </>
              )}
            </h3>
            {items.map((item) => {
              const itemTitle = view.plan.toc.find(
                (e) => e.level === "ITEM" && e.group_number === group && e.item_number === item,
              )?.title;
              return (
                <div key={item} className="layout-item">
                  <h4>{itemTitle ? `${itemLabel(group, item)} · ${itemTitle}` : itemLabel(group, item)}</h4>
                  <ul className="layout-activities">
                    {inGroup
                      .filter(({ a }) => (a.item_number ?? 0) === item)
                      .map(({ a, index }) => {
                        const toc = tocOf(a.activity_id);
                        const title = toc?.title ?? "Atividade";
                        const up = neighbour(index, -1);
                        const down = neighbour(index, 1);
                        return (
                          <li key={a.activity_id} aria-label={title}>
                            <div className="layout-activity-head">
                              <strong>{title}</strong>
                              {!dirty && toc?.first_page != null && (
                                <small className="muted">
                                  {toc.last_page != null && toc.last_page !== toc.first_page
                                    ? `pp. ${toc.first_page} a ${toc.last_page}`
                                    : `p. ${toc.first_page}`}
                                </small>
                              )}
                              {!readOnly && (
                                <span className="row-actions">
                                  <button
                                    type="button"
                                    className="btn btn-secondary"
                                    aria-label={`Subir atividade ${title}`}
                                    disabled={up === undefined}
                                    onClick={() => up !== undefined && edit((list) => swap(list, index, up))}
                                  >
                                    Subir
                                  </button>
                                  <button
                                    type="button"
                                    className="btn btn-secondary"
                                    aria-label={`Descer atividade ${title}`}
                                    disabled={down === undefined}
                                    onClick={() => down !== undefined && edit((list) => swap(list, index, down))}
                                  >
                                    Descer
                                  </button>
                                </span>
                              )}
                            </div>
                            {a.pages.length === 0 ? (
                              <p className="muted">Sem comprovante anexado</p>
                            ) : (
                              <ul className="layout-pages">
                                {a.pages.map((p, i) => {
                                  const name = docName(p.document_id);
                                  const planned = dirty ? undefined : plannedPage(toc, a, i);
                                  const repeated = p.repeat_justification != null && p.repeat_justification !== "";
                                  const owner = owners.get(pageKey(p.document_id, p.page)) === index;
                                  return (
                                    <li key={`${p.document_id}-${p.page}-${i}`}>
                                      <span>
                                        {name}, página {p.page}
                                      </span>
                                      {planned && (
                                        <small className="muted">
                                          {planned.remission
                                            ? ` · ver Comprovante p. ${planned.comprovante_page}`
                                            : ` · Comprovante p. ${planned.comprovante_page}`}
                                        </small>
                                      )}
                                      {repeated && <small className="muted">{` · Repetida: ${p.repeat_justification}`}</small>}
                                      {invalid.has(`${a.activity_id}:${pageKey(p.document_id, p.page)}`) && (
                                        <small className="error">
                                          {" · Inválida: o documento ou a página não está mais disponível"}
                                        </small>
                                      )}
                                      {!readOnly && (
                                        <span className="row-actions">
                                          {repeated ? (
                                            <button
                                              type="button"
                                              className="btn btn-secondary"
                                              aria-label={`Desfazer repetição da página ${p.page} de ${name} em ${title}`}
                                              onClick={() =>
                                                editPages(index, (pages) =>
                                                  pages.map((q, n) => (n === i ? { ...q, repeat_justification: null } : q)),
                                                )
                                              }
                                            >
                                              Desfazer repetição
                                            </button>
                                          ) : (
                                            !owner && (
                                              <button
                                                type="button"
                                                className="btn btn-secondary"
                                                aria-label={`Repetir página ${p.page} de ${name} em ${title} com justificativa`}
                                                onClick={() => setRepeating({ index, page: i })}
                                              >
                                                Repetir
                                              </button>
                                            )
                                          )}
                                          <button
                                            type="button"
                                            className="btn btn-secondary"
                                            aria-label={`Subir página ${p.page} de ${name} em ${title}`}
                                            disabled={i === 0}
                                            onClick={() => editPages(index, (pages) => swap(pages, i, i - 1))}
                                          >
                                            Subir
                                          </button>
                                          <button
                                            type="button"
                                            className="btn btn-secondary"
                                            aria-label={`Descer página ${p.page} de ${name} em ${title}`}
                                            disabled={i === a.pages.length - 1}
                                            onClick={() => editPages(index, (pages) => swap(pages, i, i + 1))}
                                          >
                                            Descer
                                          </button>
                                          <button
                                            type="button"
                                            className="btn btn-danger"
                                            aria-label={`Remover página ${p.page} de ${name} em ${title}`}
                                            onClick={() => editPages(index, (pages) => pages.filter((_, n) => n !== i))}
                                          >
                                            Remover
                                          </button>
                                        </span>
                                      )}
                                    </li>
                                  );
                                })}
                              </ul>
                            )}
                            {!readOnly &&
                              (adding === a.activity_id ? (
                                <AddPageForm
                                  title={title}
                                  count={a.pages.length}
                                  documents={documents}
                                  onCancel={() => setAdding(null)}
                                  onAdd={(page, position) => {
                                    editPages(index, (pages) => [...pages.slice(0, position - 1), page, ...pages.slice(position - 1)]);
                                    setAdding(null);
                                  }}
                                />
                              ) : (
                                <div className="btn-row">
                                  <button
                                    type="button"
                                    className="btn btn-secondary"
                                    aria-label={`Acrescentar página em ${title}`}
                                    onClick={() => setAdding(a.activity_id)}
                                  >
                                    Acrescentar página
                                  </button>
                                </div>
                              ))}
                          </li>
                        );
                      })}
                  </ul>
                </div>
              );
            })}
          </section>
        );
      })}
      {repeating && (
        <RepeatDialog
          onCancel={() => setRepeating(null)}
          onSave={(justification) => {
            editPages(repeating.index, (pages) =>
              pages.map((q, n) => (n === repeating.page ? { ...q, repeat_justification: justification } : q)),
            );
            setRepeating(null);
          }}
        />
      )}
    </div>
  );
}
