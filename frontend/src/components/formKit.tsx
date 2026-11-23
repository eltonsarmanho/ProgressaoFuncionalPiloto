/* eslint-disable react-refresh/only-export-components -- one module for the shared pieces of the table forms */
import { useState, type FormEvent, type ReactNode } from "react";
import { ApiError, errorMessage, fieldErrors } from "../api/client";
import type { FieldIssue } from "../api/client";
import { FieldError } from "./FieldError";

export type Errors = Record<string, string>;

export function Field({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: (props: { id: string; "aria-invalid"?: true; "aria-describedby"?: string }) => ReactNode;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children({
        id,
        ...(error ? { "aria-invalid": true as const, "aria-describedby": `${id}-error` } : {}),
      })}
      <FieldError id={`${id}-error`} message={error} />
    </div>
  );
}

/** Shared submit flow: busy flag, 422 per field, any other error as an alert. */
export function useSubmit(action: () => Promise<void>, onChanged: () => void) {
  const [errors, setErrors] = useState<Errors>({});
  const [fileIssues, setFileIssues] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setErrors({});
    setFileIssues([]);
    setError(null);
    setBusy(true);
    try {
      await action();
      onChanged();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422 && Array.isArray(err.detail)) {
        const issues = err.detail as FieldIssue[];
        setFileIssues(issues.filter((i) => i.field === "file").map((i) => i.message));
        setErrors(fieldErrors(new ApiError(422, issues.filter((i) => i.field !== "file"))));
      } else if (err instanceof FormProblem) {
        setErrors({ [err.field]: err.message });
      } else {
        setError(errorMessage(err));
      }
    } finally {
      setBusy(false);
    }
  }
  return { submit, errors, fileIssues, error, busy };
}

export class FormProblem extends Error {
  readonly field: string;
  constructor(field: string, message: string) {
    super(message);
    this.field = field;
  }
}

export function Alert({ message }: { message: string | null }) {
  return message ? (
    <p role="alert" className="error">
      {message}
    </p>
  ) : null;
}
