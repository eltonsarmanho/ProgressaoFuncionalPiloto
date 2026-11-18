import { useState, type FormEvent } from "react";
import { activityBody } from "../activityBody";
import { errorMessage, fieldErrors, request } from "../api/client";
import type { Activity, Criterion } from "../api/types";
import { formatDecimal } from "../labels";
import { FieldError, errorProps } from "./FieldError";

/** Why the unit value cannot be typed for this item (UIM-22); null when it can. */
function noteFor(criterion: Criterion | undefined, pit: boolean): string | null {
  if (!criterion) return "A atividade ainda não tem item de pontuação: escolha o item em Editar.";
  if (pit) return "As horas de PIT do Grupo I são calculadas da carga horária e não aceitam valor manual.";
  if (criterion.mode === "CARGA_SEMANAL") {
    return "A pontuação deste item segue a carga semanal da tabela; para informar pontos use Editar.";
  }
  if (criterion.mode === "VALOR_INFORMADO") {
    return "Neste item os pontos são os pontos informados na edição da atividade (Editar).";
  }
  return null;
}

/**
 * UIM-22: one field, the unit value of the activity. The user types it, the server stores it
 * and the scoring engine (never this component) recomputes quantity x unit value.
 */
export function ScoreEditor({
  activity,
  criterion,
  pit,
  onSaved,
  onCancel,
}: {
  activity: Activity;
  criterion: Criterion | undefined;
  pit: boolean;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const typed = activity.unit_points_override;
  const [value, setValue] = useState(typed ?? criterion?.unit_points ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const note = noteFor(criterion, pit);

  async function save(unit: number | null) {
    setBusy(true);
    setErrors({});
    setError(null);
    try {
      await request("PUT", `/api/activities/${activity.id}`, {
        ...activityBody(activity),
        unit_points_override: unit,
        expected_version: activity.version,
      });
      onSaved();
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const number = value.trim() === "" ? null : Number(value);
    void save(number != null && Number.isNaN(number) ? null : number);
  }

  return (
    <div>
      <p>{activity.title}</p>
      {note ? (
        <>
          <p className="muted">{note}</p>
          <div className="btn-row">
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              Cancelar
            </button>
          </div>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          <p className="muted">
            Valor unitário da tabela: {formatDecimal(criterion?.unit_points)}. O sistema recalcula a pontuação pela
            quantidade, dentro dos limites do item.
          </p>
          <div className="field">
            <label htmlFor="unit_points_override">Valor unitário</label>
            <input
              id="unit_points_override"
              type="number"
              step="any"
              min={0}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              {...errorProps("unit_points_override", errors)}
            />
            <FieldError id="unit_points_override-error" message={errors.unit_points_override} />
          </div>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <div className="btn-row">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              Salvar valor
            </button>
            {typed != null && (
              <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void save(null)}>
                Usar valor da tabela
              </button>
            )}
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
