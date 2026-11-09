import { OctagonX } from "lucide-react";
import type { ReactNode } from "react";

/** Label + invoer + hulptekst + fout, met de juiste aria-koppelingen. */
export function Field({
  id,
  label,
  help,
  error,
  children,
}: {
  id: string;
  label: ReactNode;
  help?: ReactNode;
  error?: string;
  children: (aria: { id: string; "aria-describedby"?: string; "aria-invalid"?: boolean }) => ReactNode;
}) {
  const ids = [help ? `${id}-help` : null, error ? `${id}-fout` : null].filter(Boolean).join(" ");
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children({ id, "aria-describedby": ids || undefined, "aria-invalid": error ? true : undefined })}
      {help ? (
        <p className="help" id={`${id}-help`}>
          {help}
        </p>
      ) : null}
      {error ? (
        <p className="flex items-start gap-1.5 text-sm font-semibold text-down-ink" id={`${id}-fout`}>
          <OctagonX aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-down" />
          <span>{error}</span>
        </p>
      ) : null}
    </div>
  );
}
