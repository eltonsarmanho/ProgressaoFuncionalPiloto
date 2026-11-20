/** Inline error rendered right after its input (UI-05); `alert` makes a screen reader announce it when it appears. */
export function FieldError({ id, message, alert = false }: { id: string; message?: string; alert?: boolean }) {
  if (!message) return null;
  return (
    <p id={id} className="error field-error" role={alert ? "alert" : undefined}>
      {message}
    </p>
  );
}

/** Props that link an input to its FieldError. */
// eslint-disable-next-line react-refresh/only-export-components
export function errorProps(name: string, errors: Record<string, string>) {
  return errors[name]
    ? { "aria-invalid": true as const, "aria-describedby": `${name}-error` }
    : {};
}
