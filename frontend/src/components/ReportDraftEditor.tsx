import { useEffect, useRef, useState } from "react";
import { request } from "../api/client";
import type { DraftEntry, DraftSection, ReportDraftView, WordingJob } from "../api/generated";
import { generationErrorMessage, isConflict } from "../generationErrors";
import { usePolling } from "../hooks/usePolling";
import { ENTRY_SOURCE_LABELS, GENERATION_CODE_LABELS, alertText, formatCount, itemLabel } from "../labels";

/** REL-07: the longest text of an entry or of a section the server accepts. */
export const MAX_TEXT_LENGTH = 20_000;

const entryKey = (activityId: string) => `e:${activityId}`;
const sectionKey = (key: string) => `s:${key}`;

/** The counter of a text: turns to an error colour above the limit. */
function Counter({ length }: { length: number }) {
  const over = length > MAX_TEXT_LENGTH;
  return (
    <small className={over ? "error" : "muted"}>{`${formatCount(length)} / ${formatCount(MAX_TEXT_LENGTH)}`}</small>
  );
}

/**
 * UIG-02, UIG-08: the report draft, one card per section, a text box per activity. A text is saved when the
 * user leaves the box, with the `version` the server last sent; a 409 reloads the draft and says so.
 * What was typed and not saved stays in `typed` until it is saved.
 *
 * The wording of a section is a background task: while one is GERANDO the screen asks the server every
 * 3 s, and when it ends the draft is reloaded; the text typed and not saved in the other sections stays.
 */
export function ReportDraftEditor({ processId, readOnly = false }: { processId: string; readOnly?: boolean }) {
  const [view, setView] = useState<ReportDraftView | null>(null);
  const [typed, setTyped] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const [jobs, setJobs] = useState<Record<string, WordingJob>>({});
  const jobsRef = useRef<Record<string, WordingJob>>({});
  const [reloads, setReloads] = useState(0);
  const load = () => setReloads((n) => n + 1);

  useEffect(() => {
    let cancelled = false;
    request<ReportDraftView>("GET", `/api/processes/${processId}/report-draft`)
      .then((found) => {
        if (!cancelled) setView(found);
      })
      .catch((err) => {
        if (!cancelled) setError(generationErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [processId, reloads]);

  /** Keeps the last job of each section; the sections whose job just left GERANDO are reloaded. */
  function applyJobs(found: WordingJob[]) {
    const before = jobsRef.current;
    const next = { ...before, ...Object.fromEntries(found.map((j) => [j.section_key, j])) };
    jobsRef.current = next;
    setJobs(next);
    const ended = found.filter((j) => j.state !== "GERANDO" && before[j.section_key]?.state === "GERANDO");
    if (ended.length === 0) return;
    const keys = new Set(ended.map((j) => j.section_key));
    setTyped((all) => {
      const rest = { ...all };
      for (const section of view?.sections ?? []) {
        if (!keys.has(section.key)) continue;
        delete rest[sectionKey(section.key)];
        for (const entry of section.entries) delete rest[entryKey(entry.activity_id)];
      }
      return rest;
    });
    load();
  }

  function loadJobs() {
    request<WordingJob[]>("GET", `/api/processes/${processId}/report-draft/wording`)
      .then(applyJobs)
      .catch((err) => setError(generationErrorMessage(err)));
  }

  useEffect(() => {
    loadJobs();
    // the jobs are read once when the editor opens; polling takes over while one runs
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processId]);

  usePolling(loadJobs, Object.values(jobs).some((j) => j.state === "GERANDO"));

  async function askWording(key: string) {
    setError(null);
    try {
      applyJobs([await request<WordingJob>("POST", `/api/processes/${processId}/report-draft/sections/${key}/wording`)]);
      load(); // the first request saves the proposal: the version of the draft changed
    } catch (err) {
      setError(generationErrorMessage(err));
      if (isConflict(err)) loadJobs();
    }
  }

  const forget = (key: string) =>
    setTyped((all) => {
      const rest = { ...all };
      delete rest[key];
      return rest;
    });

  /** One write; success reloads the draft (version, sections and empty sections), a 409 reloads and warns. */
  async function write(method: "PUT" | "POST", path: string, body: unknown, key?: string) {
    setError(null);
    try {
      await request(method, `/api/processes/${processId}/report-draft/${path}`, body);
      if (key) forget(key);
    } catch (err) {
      setError(generationErrorMessage(err));
      if (!isConflict(err)) return;
    }
    load();
  }

  if (!view) {
    return error ? (
      <p role="alert" className="error">
        {error}
      </p>
    ) : (
      <p>Carregando o rascunho…</p>
    );
  }

  const byId = new Map(view.activities.map((a) => [a.id, a]));
  const itemName = (group: number | null, item: number | null) =>
    view.item_names.find((n) => n.group_number === group && n.item_number === item)?.name;

  function saveEntry(entry: DraftEntry) {
    const key = entryKey(entry.activity_id);
    const text = typed[key];
    if (text === undefined) return;
    if (text === entry.text) return forget(key);
    if (text.length > MAX_TEXT_LENGTH) return;
    void write("PUT", `entries/${entry.activity_id}`, { expected_version: view!.version, text }, key);
  }

  function saveSection(section: DraftSection) {
    const key = sectionKey(section.key);
    const text = typed[key];
    if (text === undefined) return;
    if (text === section.free_text) return forget(key);
    if (text.length > MAX_TEXT_LENGTH) return;
    void write("PUT", `sections/${section.key}`, { expected_version: view!.version, free_text: text }, key);
  }

  function move(activityId: string, to: string) {
    if (!to) return;
    void write("POST", `entries/${activityId}/move`, { expected_version: view!.version, section_key: to });
  }

  return (
    <div className="report-editor">
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {view.alerts.map((alert) => (
        <p key={alert.code} className="doc-warning sev-ALERTA">
          {alertText(alert)}
        </p>
      ))}
      {view.sections.map((section) => {
        const empty = view.empty_sections.includes(section.key);
        const headingId = `report-section-${section.key}`;
        const sKey = sectionKey(section.key);
        const sText = typed[sKey] ?? section.free_text;
        const wording = jobs[section.key];
        const generating = wording?.state === "GERANDO";
        return (
          <section key={section.key} className="card report-section" aria-labelledby={headingId}>
            <h3 id={headingId}>
              {section.key} {section.title}
            </h3>
            {empty && <p className="muted">Seção vazia: não aparece no documento.</p>}
            {generating && <p role="status">Gerando a redação…</p>}
            {wording?.state === "FALHOU" && (
              <p role="alert" className="error">
                A redação falhou: {(wording.error_code && GENERATION_CODE_LABELS[wording.error_code]) ?? "tente de novo."}
              </p>
            )}
            {!readOnly && (
              <div className="btn-row">
                <button
                  type="button"
                  className="btn btn-secondary"
                  aria-label={`Pedir redação de ${section.key}`}
                  title={`Pedir redação de ${section.key} ${section.title}`}
                  disabled={generating || section.entries.length === 0}
                  onClick={() => void askWording(section.key)}
                >
                  Pedir redação
                </button>
              </div>
            )}
            {section.warnings.map((warning, i) => (
              <p key={`${warning.code}-${i}`} className="doc-warning sev-ALERTA">
                {alertText(warning)}
              </p>
            ))}
            {section.entries.length > 0 && (
              <ul className="report-entries">
                {section.entries.map((entry) => {
                  const activity = byId.get(entry.activity_id);
                  const title = activity?.title ?? "Atividade";
                  const key = entryKey(entry.activity_id);
                  const text = typed[key] ?? entry.text;
                  const over = text.length > MAX_TEXT_LENGTH;
                  const dirty = typed[key] !== undefined && typed[key] !== entry.text;
                  const name = activity ? itemName(activity.group_number, activity.item_number) : undefined;
                  return (
                    <li key={entry.activity_id}>
                      <div className="report-entry-head">
                        <strong>{title}</strong>
                        {activity && (
                          <small className="muted">
                            {itemLabel(activity.group_number, activity.item_number)}
                            {name ? ` · ${name}` : ""}
                          </small>
                        )}
                        <span className={`badge source-${entry.source}`}>{ENTRY_SOURCE_LABELS[entry.source]}</span>
                      </div>
                      {entry.warnings.map((warning, i) => (
                        <p key={`${warning.code}-${i}`} className="doc-warning sev-ALERTA">
                          {alertText(warning)}
                        </p>
                      ))}
                      <label htmlFor={`entry-${entry.activity_id}`} className="visually-hidden">
                        {`Texto de ${title}`}
                      </label>
                      <textarea
                        id={`entry-${entry.activity_id}`}
                        rows={4}
                        value={text}
                        readOnly={readOnly}
                        aria-invalid={over ? true : undefined}
                        onChange={(e) => setTyped((all) => ({ ...all, [key]: e.target.value }))}
                        onBlur={() => saveEntry(entry)}
                      />
                      <div className="report-entry-foot">
                        <Counter length={text.length} />
                        {over && <small className="error">Acima do limite: o texto não é salvo.</small>}
                        {dirty && !readOnly && (
                          <>
                            <small className="muted">Alterações não salvas</small>
                            <button
                              type="button"
                              className="btn btn-primary"
                              aria-label={`Salvar ${title}`}
                              disabled={over}
                              onClick={() => saveEntry(entry)}
                            >
                              Salvar
                            </button>
                          </>
                        )}
                        {!readOnly && (
                          <select
                            aria-label={`Mover ${title} para`}
                            value=""
                            onChange={(e) => move(entry.activity_id, e.target.value)}
                          >
                            <option value="">Mover para…</option>
                            {view.sections
                              .filter((s) => s.key !== section.key)
                              .map((s) => (
                                <option key={s.key} value={s.key}>
                                  {s.key} {s.title}
                                </option>
                              ))}
                          </select>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
            <label htmlFor={`free-${section.key}`}>{`Texto livre da seção ${section.key}`}</label>
            <textarea
              id={`free-${section.key}`}
              rows={2}
              value={sText}
              readOnly={readOnly}
              aria-invalid={sText.length > MAX_TEXT_LENGTH ? true : undefined}
              onChange={(e) => setTyped((all) => ({ ...all, [sKey]: e.target.value }))}
              onBlur={() => saveSection(section)}
            />
            <Counter length={sText.length} />
          </section>
        );
      })}
    </div>
  );
}
