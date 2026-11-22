import { useState } from "react";
import { saveOpinion, type Opinion, type OpinionConclusion } from "../api/board";
import { boardFailure } from "../boardErrors";
import { OPINION_CONCLUSION_LABELS, formatCount } from "../labels";
import { FieldError } from "./FieldError";

/** PAR-13: the longest text of the notes of the board the server accepts. */
export const MAX_NOTES_LENGTH = 5000;

const CONCLUSIONS: OpinionConclusion[] = ["FAVORAVEL", "DESFAVORAVEL"];

const fieldProps = (field: string, errors: Record<string, string>) => ({
  id: `opinion-${field}`,
  "aria-invalid": errors[field] ? (true as const) : undefined,
  "aria-describedby": errors[field] ? `opinion-${field}-error` : undefined,
});

/**
 * PAR-01, PAR-12, PAR-13, BNAV-02: the fields of the Parecer the person fills in the Etapa 6. The
 * conclusion is two radio buttons with no initial selection: the screen reads no total and no
 * minimum and never suggests it. No justification is asked (regra 5).
 *
 * The form is controlled by the page, as the one of the ordinance: `opinion` is what the server last
 * sent, `onChanged` receives what a save returned and `onStale` asks the page to read the board again
 * after a 409.
 */
export function OpinionForm({
  processId,
  opinion,
  readOnly = false,
  readOnlyReason,
  onChanged,
  onStale,
}: {
  processId: string;
  opinion: Opinion;
  readOnly?: boolean;
  readOnlyReason?: string;
  onChanged: (next: Opinion) => void;
  onStale?: () => void;
}) {
  const [conclusion, setConclusion] = useState<OpinionConclusion | null>(opinion.conclusion);
  const [date, setDate] = useState(opinion.opinion_date ?? "");
  const [place, setPlace] = useState(opinion.place ?? "");
  const [notes, setNotes] = useState(opinion.notes ?? "");
  const [seen, setSeen] = useState(opinion.version);
  if (seen !== opinion.version) {
    setSeen(opinion.version);
    setConclusion(opinion.conclusion);
    setDate(opinion.opinion_date ?? "");
    setPlace(opinion.place ?? "");
    setNotes(opinion.notes ?? "");
  }

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const tooLong = notes.length > MAX_NOTES_LENGTH;
  const locked = readOnly || busy;

  async function save() {
    setErrors({});
    setMessage(null);
    setBusy(true);
    try {
      onChanged(
        await saveOpinion(processId, {
          conclusion,
          opinion_date: date || null,
          place: place.trim() || null,
          notes: notes || null,
          expected_version: opinion.version,
        }),
      );
    } catch (err) {
      const failure = boardFailure(err);
      setErrors(failure.fields);
      setMessage(failure.message);
      if (failure.stale) onStale?.();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="opinion-form">
      {readOnly && readOnlyReason && <p className="muted">{readOnlyReason}</p>}
      <fieldset>
        <legend>Conclusão do Parecer</legend>
        {CONCLUSIONS.map((value) => (
          <label key={value} className="radio">
            <input
              type="radio"
              name="opinion-conclusion"
              value={value}
              checked={conclusion === value}
              disabled={locked}
              onChange={() => setConclusion(value)}
            />
            {OPINION_CONCLUSION_LABELS[value]}
          </label>
        ))}
        <FieldError id="opinion-conclusion-error" message={errors.conclusion} />
      </fieldset>

      <div className="field">
        <label htmlFor="opinion-opinion_date">Data do Parecer</label>
        <input
          {...fieldProps("opinion_date", errors)}
          type="date"
          value={date}
          disabled={locked}
          onChange={(event) => setDate(event.target.value)}
        />
        <FieldError id="opinion-opinion_date-error" message={errors.opinion_date} />
      </div>

      <div className="field">
        <label htmlFor="opinion-place">Local</label>
        <input
          {...fieldProps("place", errors)}
          type="text"
          value={place}
          disabled={locked}
          onChange={(event) => setPlace(event.target.value)}
        />
        <FieldError id="opinion-place-error" message={errors.place} />
      </div>

      <div className="field">
        <label htmlFor="opinion-notes">Observações da banca</label>
        <textarea
          {...fieldProps("notes", errors)}
          rows={5}
          value={notes}
          disabled={locked}
          onChange={(event) => setNotes(event.target.value)}
        />
        <small className={tooLong ? "error" : "muted"}>
          {`${formatCount(notes.length)} / ${formatCount(MAX_NOTES_LENGTH)}`}
        </small>
        <FieldError id="opinion-notes-error" message={errors.notes} />
      </div>

      {message && (
        <p role="alert" className="error">
          {message}
        </p>
      )}
      <div className="btn-row">
        <button type="button" className="btn btn-primary" disabled={locked || tooLong} onClick={() => void save()}>
          Salvar minuta do Parecer
        </button>
      </div>
    </div>
  );
}
