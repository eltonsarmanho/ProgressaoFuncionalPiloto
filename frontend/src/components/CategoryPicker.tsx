import { useId, type Ref } from "react";
import type { ScoringGroup } from "../api/types";
import { GROUP_NAMES, roman } from "../labels";
import { FieldError } from "./FieldError";

export type CategoryValue = { group_number: number; item_number: number };

/**
 * SEC-04: the category of an activity, chosen from the items of the chosen table, grouped by
 * group. Picking applies at once (`onChange`): there is no justification. Without a table
 * (`groups` empty) it only tells the user to choose one.
 */
export function CategoryPicker({
  groups,
  value,
  onChange,
  label,
  hideLabel = true,
  error,
  disabled = false,
  selectRef,
  id: fixedId,
}: {
  groups: ScoringGroup[];
  value: { group_number: number | null; item_number: number | null } | null;
  onChange: (value: CategoryValue) => void;
  /** The accessible name of the select ("Categoria de <título>"). */
  label: string;
  /** The label is only for assistive technology unless the form wants it seen. */
  hideLabel?: boolean;
  error?: string;
  disabled?: boolean;
  selectRef?: Ref<HTMLSelectElement>;
  /** A fixed id for the select, for a form that moves the focus to it; one is generated otherwise. */
  id?: string;
}) {
  const generatedId = useId();
  const id = fixedId ?? generatedId;
  const errorId = `${id}-error`;
  const current = value?.group_number != null && value.item_number != null ? `${value.group_number}.${value.item_number}` : "";

  if (groups.length === 0) {
    return <p className="muted">Escolha a tabela de pontuação na Etapa 4 para poder escolher a categoria.</p>;
  }

  return (
    <div className="category-picker">
      <label htmlFor={id} className={hideLabel ? "visually-hidden" : undefined}>
        {label}
      </label>
      <select
        id={id}
        ref={selectRef}
        value={current}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        onChange={(event) => {
          if (event.target.value === "") return;
          const [group, item] = event.target.value.split(".").map(Number);
          onChange({ group_number: group, item_number: item });
        }}
      >
        <option value="">Escolha a categoria</option>
        {groups.map((g) => (
          <optgroup key={g.number} label={`${roman(g.number)} · ${g.name || GROUP_NAMES[g.number]}`}>
            {g.criteria.map((c) => (
              <option key={c.item_number} value={`${c.group_number}.${c.item_number}`}>
                {`${roman(c.group_number)}.${c.item_number} · ${c.description}`}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <FieldError id={errorId} message={error} alert />
    </div>
  );
}
