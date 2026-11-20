import { useEffect, useRef, useState } from "react";
import { isValid } from "../activityList";
import type { Activity, DocumentSummary, ScoringGroup, ScoringRow } from "../api/types";
import { ActivityForm } from "./ActivityForm";
import type { RowFeedback } from "./ActivityRow";
import { InvalidActivitiesSection } from "./InvalidActivitiesSection";
import { Modal } from "./Modal";
import { ValidActivitiesSection } from "./ValidActivitiesSection";

type PendingFocus = { id: string; neighborId: string | null; section: string | null };

const titlesIn = (root: HTMLElement | null) => [...(root?.querySelectorAll<HTMLElement>("[data-activity-title]") ?? [])];

/**
 * SEC-01, SEC-08, SEC-09, SEC-12: the two sections of the Etapa 3. It splits the list by the
 * validity the server sent and owns the edit dialog. A write never moves an activity by itself:
 * `onChanged` makes the parent reload the list, and the activity lands in the section its new
 * validity says (a corrected date, a reopened rejection), without reloading the page.
 */
export function ActivityWorkspace({
  processId,
  activities,
  rows,
  groups,
  documents,
  onChanged,
  loadFailures = 0,
}: {
  processId: string;
  activities: Activity[];
  rows: ScoringRow[];
  groups: ScoringGroup[];
  documents: DocumentSummary[];
  onChanged: () => void;
  /** Counts the reloads that failed: the focus a failed reload was to move is dropped. */
  loadFailures?: number;
}) {
  const [editing, setEditing] = useState<Activity | null>(null);
  // `n` makes each announcement and each error a new node, so the same text is read again.
  const [announcement, setAnnouncement] = useState({ message: "", n: 0 });
  const [rowError, setRowError] = useState<{ title: string; message: string; n: number } | null>(null);
  // The reload that a failed write asks for must not take its own error away.
  const ownReload = useRef(false);
  const root = useRef<HTMLDivElement>(null);
  const pending = useRef<PendingFocus | null>(null);

  const titleOf = (id: string) => titlesIn(root.current).find((t) => t.dataset.activityTitle === id);

  /** Remembers where the focus goes if the row leaves the page with the reload. */
  const remember = (id: string) => {
    const row = titleOf(id)?.closest("li");
    const neighbor = row?.nextElementSibling ?? row?.previousElementSibling;
    pending.current = {
      id,
      neighborId: neighbor?.querySelector<HTMLElement>("[data-activity-title]")?.dataset.activityTitle ?? null,
      section: row?.closest("section")?.getAttribute("aria-labelledby") ?? null,
    };
  };

  /** Announces the result, or shows the error where a reload cannot remove it. */
  const feedback: RowFeedback = {
    start: () => setRowError(null),
    done: (id, message) => {
      setAnnouncement((current) => ({ message, n: current.n + 1 }));
      setRowError(null);
      remember(id);
    },
    fail: (id, title, message, reloads) => {
      setRowError((current) => ({ title, message, n: (current?.n ?? 0) + 1 }));
      ownReload.current = reloads;
      remember(id);
    },
  };

  // A reload that failed leaves the list as it was: the focus it was to move must not move later,
  // and the error it was to outlive is still the newest word on the list.
  useEffect(() => {
    pending.current = null;
    ownReload.current = false;
  }, [loadFailures]);

  // The error of a row stays through the reload its own failure caused and goes with the next one.
  useEffect(() => {
    if (ownReload.current) ownReload.current = false;
    else setRowError(null);
  }, [activities]);

  // After a reload the row may be gone (it changed section): the focus goes to its new place, to the
  // neighbor it left or to the title of its section, and never stays on the <body>.
  useEffect(() => {
    const target = pending.current;
    if (!target) return;
    pending.current = null;
    const active = document.activeElement;
    if (active && active !== document.body) return;
    const fallback = target.section
      ? root.current?.querySelector<HTMLElement>(`section[aria-labelledby="${target.section}"] [data-focus-fallback]`)
      : null;
    const next = titleOf(target.id) ?? (target.neighborId ? titleOf(target.neighborId) : null) ?? fallback;
    next?.focus();
  }, [activities]);

  const done = () => {
    if (editing) feedback.done(editing.id, `Atividade ${editing.title} salva`);
    setEditing(null);
    onChanged();
  };

  return (
    <div className="activity-workspace" ref={root}>
      <div role="status" className="visually-hidden">
        {announcement.message && <span key={announcement.n}>{announcement.message}</span>}
      </div>
      {rowError && (
        <p key={rowError.n} role="alert" className="error">
          {`${rowError.title}: ${rowError.message}`}
        </p>
      )}
      <ValidActivitiesSection
        processId={processId}
        activities={activities.filter(isValid)}
        rows={rows}
        groups={groups}
        documents={documents}
        onEdit={setEditing}
        onChanged={onChanged}
        feedback={feedback}
      />
      <InvalidActivitiesSection
        activities={activities.filter((a) => !isValid(a))}
        groups={groups}
        onEdit={setEditing}
        onChanged={onChanged}
        feedback={feedback}
      />
      {editing && (
        <Modal title="Editar atividade" onClose={() => setEditing(null)}>
          <ActivityForm
            key={`edit-${editing.id}`}
            processId={processId}
            groups={groups}
            activity={editing}
            onSaved={done}
            onCancel={() => setEditing(null)}
          />
        </Modal>
      )}
    </div>
  );
}
