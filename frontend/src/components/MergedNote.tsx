import { useState } from "react";
import { errorMessage, fieldErrors, request } from "../api/client";
import type { Activity, MergedRef } from "../api/types";

/**
 * DUP-07: "N duplicadas mescladas" on the kept activity, with the title of each and the button
 * "Não é duplicada", which restores it at once (no confirmation, no justification). The parent
 * reloads the list when `onSeparated` runs.
 */
export function MergedNote({ merged, onSeparated }: { merged: MergedRef[]; onSeparated: (restored: Activity) => void }) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (merged.length === 0) return null;

  async function separate(ref: MergedRef) {
    setError(null);
    setBusy(true);
    try {
      onSeparated(await request<Activity>("POST", `/api/activities/${ref.id}/separate`));
    } catch (err) {
      setError(Object.values(fieldErrors(err))[0] ?? errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="merged-note">
      <p className="muted">{merged.length === 1 ? "1 duplicada mesclada" : `${merged.length} duplicadas mescladas`}</p>
      <ul className="merged-list">
        {merged.map((m) => (
          <li key={m.id}>
            <span>{m.title}</span>{" "}
            <button
              type="button"
              className="btn btn-secondary"
              aria-label={`Não é duplicada: ${m.title}`}
              disabled={busy}
              onClick={() => void separate(m)}
            >
              Não é duplicada
            </button>
          </li>
        ))}
      </ul>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </div>
  );
}
