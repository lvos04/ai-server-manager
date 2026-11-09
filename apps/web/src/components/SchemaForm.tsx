"use client";

import { OctagonX } from "lucide-react";
import { emptyDraft, setAt, type Draft, type Errors, type FieldNode } from "@/lib/schema-form";
import { Button } from "@/components/ui/button";

type Path = (string | number)[];

interface Props {
  node: FieldNode;
  draft: Draft;
  errors: Errors;
  disabled?: boolean;
  idPrefix: string;
  onChange: (next: Draft) => void;
}

const pathKey = (p: Path) => p.join(".");
const pathId = (prefix: string, p: Path) => `${prefix}-${p.join("-") || "root"}`;

/** Formulier voor een besluitwaarde. Alle velden starten leeg of met de huidige waarde — nooit met een voorbeeld. */
export function SchemaForm({ node, draft, errors, disabled, idPrefix, onChange }: Props) {
  const update = (path: Path, value: Draft) => onChange(setAt(draft, path, value));
  const rootError = errors[""];
  return (
    <div className="stack">
      {rootError ? (
        <p className="form-error" role="alert">
          {rootError}
        </p>
      ) : null}
      <FieldView node={node} value={draft} path={[]} errors={errors} disabled={disabled} idPrefix={idPrefix} update={update} root />
    </div>
  );
}

function Help({ id, text }: { id: string; text?: string }) {
  return text ? (
    <p className="help" id={`${id}-help`}>
      {text}
    </p>
  ) : null;
}

function ErrorText({ id, text }: { id: string; text?: string }) {
  return text ? (
    <p className="flex items-start gap-1.5 text-sm font-semibold text-down-ink" id={`${id}-fout`}>
      <OctagonX aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-down" />
      <span>{text}</span>
    </p>
  ) : null;
}

function describedBy(id: string, help?: string, error?: string) {
  const ids = [help ? `${id}-help` : null, error ? `${id}-fout` : null].filter(Boolean).join(" ");
  return ids || undefined;
}

function FieldView({
  node,
  value,
  path,
  errors,
  disabled,
  idPrefix,
  update,
  root,
  itemLabel,
}: {
  node: FieldNode;
  value: Draft;
  path: Path;
  errors: Errors;
  disabled?: boolean;
  idPrefix: string;
  update: (path: Path, value: Draft) => void;
  root?: boolean;
  itemLabel?: string;
}) {
  const id = pathId(idPrefix, path);
  const error = errors[pathKey(path)];
  const label = itemLabel ?? node.label;
  const optional = !node.required || node.nullable;
  const labelText = (
    <>
      {label}
      {optional && node.kind !== "list" && node.kind !== "object" && node.kind !== "const" ? <span className="muted"> (optioneel)</span> : null}
    </>
  );

  switch (node.kind) {
    case "object": {
      const obj = (value && typeof value === "object" && !Array.isArray(value) ? value : {}) as Record<string, Draft>;
      const inner = node.fields.map((f) => (
        <FieldView
          key={f.key}
          node={f}
          value={obj[f.key] ?? emptyDraft(f)}
          path={[...path, f.key]}
          errors={errors}
          disabled={disabled}
          idPrefix={idPrefix}
          update={update}
        />
      ));
      if (root) return <>{inner}</>;
      return (
        <fieldset aria-describedby={describedBy(id, undefined, error)}>
          <legend>{label}</legend>
          <div className="stack">{inner}</div>
          <ErrorText id={id} text={error} />
        </fieldset>
      );
    }
    case "list": {
      const items = Array.isArray(value) ? value : [];
      const full = node.maxItems !== undefined && items.length >= node.maxItems;
      return (
        <fieldset aria-describedby={describedBy(id, node.help, error)} data-testid={`lijst-${pathKey(path)}`}>
          <legend>
            {label}
            {!node.required || !node.minItems ? <span className="muted"> (optioneel)</span> : null}
          </legend>
          <div className="stack" style={{ gap: 8 }}>
            <Help id={id} text={node.help} />
            {items.length === 0 ? <p className="meta">Nog niets toegevoegd.</p> : null}
            {items.map((item, i) => (
              <div className="list-item" key={i}>
                <FieldView
                  node={node.item}
                  value={item}
                  path={[...path, i]}
                  errors={errors}
                  disabled={disabled}
                  idPrefix={idPrefix}
                  update={update}
                  itemLabel={`${label} ${i + 1}`}
                />
                <Button
                 
                  variant="gevaar"
                  uit={disabled}
                  onClick={() => update(path, items.filter((_, j) => j !== i))}
                >
                  Verwijder<span className="sr-only">{` ${label} ${i + 1}`}</span>
                </Button>
              </div>
            ))}
            <div className="row">
              <Button
                variant="secundair"
                uit={disabled || full}
                onClick={() => update(path, [...items, emptyDraft(node.item)])}
              >
                {`Toevoegen: ${label.toLowerCase()}`}
              </Button>
            </div>
            <ErrorText id={id} text={error} />
          </div>
        </fieldset>
      );
    }
    case "boolean": {
      if (node.nullable || !node.required) {
        const v = value === true ? "ja" : value === false ? "nee" : "";
        return (
          <div className="field">
            <label htmlFor={id}>{label}</label>
            <select
              id={id}
              value={v}
              disabled={disabled}
              aria-describedby={describedBy(id, node.help, error)}
              aria-invalid={error ? true : undefined}
              onChange={(e) => update(path, e.target.value === "ja" ? true : e.target.value === "nee" ? false : null)}
            >
              <option value="">Onbekend / niet ingevuld</option>
              <option value="ja">Ja</option>
              <option value="nee">Nee</option>
            </select>
            <Help id={id} text={node.help} />
            <ErrorText id={id} text={error} />
          </div>
        );
      }
      return (
        <fieldset aria-describedby={describedBy(id, node.help, error)} aria-invalid={error ? true : undefined}>
          <legend>{label}</legend>
          <div className="row" style={{ gap: 16 }}>
            {(["ja", "nee"] as const).map((opt) => (
              <label key={opt} className="choice">
                <input
                  type="radio"
                  name={id}
                  value={opt}
                  disabled={disabled}
                  checked={opt === "ja" ? value === true : value === false}
                  onChange={() => update(path, opt === "ja")}
                />
                {opt === "ja" ? "Ja" : "Nee"}
              </label>
            ))}
          </div>
          <Help id={id} text={node.help} />
          <ErrorText id={id} text={error} />
        </fieldset>
      );
    }
    case "const": {
      if (node.value === true) {
        return (
          <div className="field">
            <label className="choice" htmlFor={id}>
              <input
                id={id}
                type="checkbox"
                checked={value === true}
                disabled={disabled}
                aria-describedby={describedBy(id, node.help, error)}
                aria-invalid={error ? true : undefined}
                onChange={(e) => update(path, e.target.checked ? true : null)}
              />
              <span>
                Ik bevestig: {label.charAt(0).toLowerCase() + label.slice(1)}
              </span>
            </label>
            <Help id={id} text={node.help} />
            <ErrorText id={id} text={error} />
          </div>
        );
      }
      return (
        <div className="field">
          <span className="label">{label}</span>
          <p style={{ margin: 0 }}>{node.value === false ? "Nee (vast, niet wijzigbaar)" : String(node.value)}</p>
          <Help id={id} text={node.help} />
        </div>
      );
    }
    case "enum": {
      return (
        <div className="field">
          <label htmlFor={id}>{labelText}</label>
          <select
            id={id}
            value={typeof value === "string" ? value : ""}
            disabled={disabled}
            aria-describedby={describedBy(id, node.help, error)}
            aria-invalid={error ? true : undefined}
            onChange={(e) => update(path, e.target.value)}
          >
            <option value="">— maak een keuze —</option>
            {node.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <Help id={id} text={node.help} />
          <ErrorText id={id} text={error} />
        </div>
      );
    }
    case "number":
    case "text": {
      const isDate = node.kind === "text" && node.format === "date";
      return (
        <div className="field">
          <label htmlFor={id}>{labelText}</label>
          <input
            id={id}
            type={isDate ? "date" : "text"}
            inputMode={node.kind === "number" ? (node.integer ? "numeric" : "decimal") : undefined}
            value={typeof value === "string" ? value : ""}
            disabled={disabled}
            autoComplete="off"
            spellCheck={false}
            maxLength={node.kind === "text" ? node.maxLength : undefined}
            aria-describedby={describedBy(id, node.help, error)}
            aria-invalid={error ? true : undefined}
            onChange={(e) => update(path, e.target.value)}
          />
          <Help id={id} text={node.help} />
          <ErrorText id={id} text={error} />
        </div>
      );
    }
  }
}
