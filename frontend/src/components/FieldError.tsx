/** Inline error rendered right after its input (UI-05). */
export function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} className="error field-error">
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
