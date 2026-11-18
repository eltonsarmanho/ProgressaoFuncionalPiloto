import { useEffect, useState } from "react";
import { request } from "../api/client";
import type { LayoutActivity, LayoutView, PageRef, TocEntry } from "../api/generated";
import type { DocumentSummary } from "../api/types";
import { generationErrorMessage, isConflict } from "../generationErrors";
import { itemLabel, roman } from "../labels";

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
                                      {!readOnly && (
                                        <span className="row-actions">
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
    </div>
  );
}
