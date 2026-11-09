/**
 * Formulier uit het JSON-schema van een besluit (pydantic-export). Pure functies, getest met vitest.
 *
 * Regels:
 * - Velden starten LEEG (of met de huidige waarde van het besluit). Er wordt nooit een voorbeeldwaarde ingevuld.
 * - Een verplichte ja/nee-vraag heeft geen standaardantwoord (keuzerondjes, niets geselecteerd).
 * - `const: true` (bijv. "harde stop") is een verplichte bevestiging; `const: false` is een vast gegeven.
 * - De server valideert altijd opnieuw; zijn foutmeldingen (Engels uit pydantic) worden naar het Nederlands vertaald.
 */

import { enumLabel, fieldLabel, FIELD_HELP } from "./decisions";
import type { JsonSchema } from "./types";

interface Base {
  key: string;
  label: string;
  help?: string;
  required: boolean;
  nullable: boolean;
}

export type FieldNode =
  | (Base & { kind: "text"; minLength?: number; maxLength?: number; pattern?: string; format?: "date" })
  | (Base & { kind: "number"; integer: boolean; min?: number; max?: number; exclusiveMin?: number })
  | (Base & { kind: "boolean" })
  | (Base & { kind: "const"; value: string | number | boolean })
  | (Base & { kind: "enum"; options: { value: string; label: string }[] })
  | (Base & { kind: "list"; item: FieldNode; minItems?: number; maxItems?: number })
  | (Base & { kind: "object"; fields: FieldNode[] });

export type Draft = string | boolean | null | Draft[] | { [k: string]: Draft };

export function resolveRef(schema: JsonSchema, root: JsonSchema): JsonSchema {
  if (!schema.$ref) return schema;
  const m = /^#\/\$defs\/(.+)$/.exec(schema.$ref);
  const target = m && root.$defs ? root.$defs[m[1] ?? ""] : undefined;
  if (!target) throw new Error(`Onbekende schemaverwijzing: ${schema.$ref}`);
  return target;
}

function typeOf(s: JsonSchema): string | undefined {
  return Array.isArray(s.type) ? s.type.find((t) => t !== "null") : s.type;
}

export function describe(schema: JsonSchema, root: JsonSchema, key = "", required = true): FieldNode {
  let s = resolveRef(schema, root);
  let nullable = false;
  if (s.anyOf) {
    const rest = s.anyOf.filter((a) => a.type !== "null");
    nullable = rest.length < s.anyOf.length;
    if (rest.length !== 1) throw new Error(`Niet-ondersteund schema voor ${key || "waarde"}`);
    s = resolveRef(rest[0] as JsonSchema, root);
  }
  const help = [schema.description ?? s.description, FIELD_HELP[key]].filter(Boolean).join(" ") || undefined;
  const base: Base = { key, label: fieldLabel(key, s.title ?? key), help, required, nullable };
  if (s.const !== undefined) return { ...base, kind: "const", value: s.const };
  const t = typeOf(s);
  if (s.enum) {
    return { ...base, kind: "enum", options: s.enum.map((v) => ({ value: String(v), label: enumLabel(String(v)) })) };
  }
  if (t === "object" || s.properties) {
    const req = new Set(s.required ?? []);
    const fields = Object.entries(s.properties ?? {}).map(([k, sub]) => describe(sub, root, k, req.has(k)));
    return { ...base, kind: "object", fields };
  }
  if (t === "array") {
    if (!s.items) throw new Error(`Lijst zonder itemschema: ${key}`);
    const item = describe(s.items, root, key, true);
    return { ...base, kind: "list", item: { ...item, label: base.label }, minItems: s.minItems, maxItems: s.maxItems };
  }
  if (t === "boolean") return { ...base, kind: "boolean" };
  if (t === "integer" || t === "number") {
    return {
      ...base,
      kind: "number",
      integer: t === "integer",
      min: s.minimum,
      max: s.maximum,
      exclusiveMin: s.exclusiveMinimum,
    };
  }
  return {
    ...base,
    kind: "text",
    minLength: s.minLength,
    maxLength: s.maxLength,
    pattern: s.pattern,
    format: s.format === "date" ? "date" : undefined,
  };
}

/** Lege invoer voor een nieuw veld of lijstitem (geen voorbeeldwaarde). */
export function emptyDraft(node: FieldNode): Draft {
  switch (node.kind) {
    case "object":
      return Object.fromEntries(node.fields.map((f) => [f.key, emptyDraft(f)]));
    case "list":
      return [];
    case "boolean":
    case "const":
      return null;
    default:
      return "";
  }
}

/** Huidige waarde van het besluit → invoer. */
export function toDraft(node: FieldNode, value: unknown): Draft {
  if (value === null || value === undefined) return emptyDraft(node);
  switch (node.kind) {
    case "object": {
      const obj = (typeof value === "object" && value !== null ? value : {}) as Record<string, unknown>;
      return Object.fromEntries(node.fields.map((f) => [f.key, toDraft(f, obj[f.key])]));
    }
    case "list":
      return Array.isArray(value) ? value.map((v) => toDraft(node.item, v)) : [];
    case "boolean":
    case "const":
      return typeof value === "boolean" ? value : null;
    default:
      return String(value);
  }
}

export type Errors = Record<string, string>;

function join(path: string, key: string | number): string {
  return path ? `${path}.${key}` : String(key);
}

function parseNumber(raw: string): number | null {
  const t = raw.trim().replace(/\s/g, "").replace(",", ".");
  if (!/^-?\d+(\.\d+)?$/.test(t)) return null;
  return Number(t);
}

/**
 * Invoer → waarde voor de API. Lege optionele velden worden `null` (of een lege lijst); verplichte lege velden geven
 * een fout. Geeft `errors` met paden in hetzelfde formaat als de server (`pools.0`, `per_app.1.rpo_uren`).
 */
export function fromDraft(node: FieldNode, draft: Draft, path = ""): { value: unknown; errors: Errors } {
  const errors: Errors = {};
  const value = convert(node, draft, path, errors);
  return { value, errors };
}

function convert(node: FieldNode, draft: Draft, path: string, errors: Errors): unknown {
  switch (node.kind) {
    case "object": {
      const d = (draft && typeof draft === "object" && !Array.isArray(draft) ? draft : {}) as Record<string, Draft>;
      const out: Record<string, unknown> = {};
      for (const f of node.fields) {
        const v = convert(f, d[f.key] ?? emptyDraft(f), join(path, f.key), errors);
        if (v !== undefined) out[f.key] = v;
      }
      return out;
    }
    case "list": {
      const items = Array.isArray(draft) ? draft : [];
      const out = items.map((d, i) => convert(node.item, d, join(path, i), errors));
      if (node.required && node.minItems && out.length < node.minItems) {
        errors[path] = node.minItems === 1 ? "Voeg minstens één item toe." : `Voeg minstens ${node.minItems} items toe.`;
      }
      if (node.maxItems !== undefined && out.length > node.maxItems) errors[path] = `Maximaal ${node.maxItems} items.`;
      return out;
    }
    case "boolean": {
      if (typeof draft === "boolean") return draft;
      if (node.required && !node.nullable) errors[path] = "Kies ja of nee.";
      return node.nullable ? null : undefined;
    }
    case "const": {
      if (node.value === true) {
        if (draft !== true) errors[path] = "Bevestig dit om verder te gaan.";
        return true;
      }
      return node.value;
    }
    case "enum": {
      const v = typeof draft === "string" ? draft : "";
      if (!v) {
        if (node.required && !node.nullable) errors[path] = "Maak een keuze.";
        return node.nullable ? null : undefined;
      }
      if (!node.options.some((o) => o.value === v)) errors[path] = "Kies een geldige waarde.";
      return v;
    }
    case "number": {
      const raw = typeof draft === "string" ? draft.trim() : "";
      if (!raw) {
        if (node.required && !node.nullable) errors[path] = "Verplicht veld.";
        return node.nullable ? null : undefined;
      }
      const n = parseNumber(raw);
      if (n === null) {
        errors[path] = node.integer ? "Vul een geheel getal in." : "Vul een getal in.";
        return raw;
      }
      if (node.integer && !Number.isInteger(n)) errors[path] = "Vul een geheel getal in.";
      else if (node.min !== undefined && n < node.min) errors[path] = `Minimaal ${node.min}.`;
      else if (node.max !== undefined && n > node.max) errors[path] = `Maximaal ${node.max}.`;
      else if (node.exclusiveMin !== undefined && n <= node.exclusiveMin) errors[path] = `Moet groter zijn dan ${node.exclusiveMin}.`;
      return n;
    }
    case "text": {
      const raw = typeof draft === "string" ? draft.trim() : "";
      if (!raw) {
        if (node.required && !node.nullable) errors[path] = "Verplicht veld.";
        return node.nullable ? null : undefined;
      }
      if (node.maxLength !== undefined && raw.length > node.maxLength) errors[path] = `Maximaal ${node.maxLength} tekens.`;
      else if (node.pattern && !new RegExp(node.pattern).test(raw)) errors[path] = "Ongeldig formaat.";
      return raw;
    }
  }
}

/** Waarde in een draft-boom zetten (onveranderlijk). */
export function setAt(draft: Draft, path: (string | number)[], value: Draft): Draft {
  if (path.length === 0) return value;
  const [head, ...rest] = path as [string | number, ...(string | number)[]];
  if (Array.isArray(draft)) {
    const copy = [...draft];
    copy[head as number] = setAt(copy[head as number] ?? null, rest, value);
    return copy;
  }
  const obj = (draft && typeof draft === "object" ? draft : {}) as Record<string, Draft>;
  return { ...obj, [head]: setAt(obj[head as string] ?? null, rest, value) };
}

const PATTERNS: [RegExp, (m: RegExpExecArray) => string][] = [
  [/^Field required$/i, () => "Verplicht veld."],
  [/^Value error, (.+)$/i, (m) => capitalize(m[1] ?? "")],
  [/^Assertion failed, (.+)$/i, (m) => capitalize(m[1] ?? "")],
  [/^String should have at least (\d+) characters?$/i, (m) => `Minstens ${m[1]} teken${m[1] === "1" ? "" : "s"}.`],
  [/^String should have at most (\d+) characters?$/i, (m) => `Maximaal ${m[1]} tekens.`],
  [/^String should match pattern/i, () => "Ongeldig formaat."],
  [/^Input should be a valid integer/i, () => "Vul een geheel getal in."],
  [/^Input should be a valid number/i, () => "Vul een getal in."],
  [/^Input should be a valid boolean/i, () => "Kies ja of nee."],
  [/^Input should be a valid date/i, () => "Vul een geldige datum in."],
  [/^Input should be a valid string/i, () => "Vul tekst in."],
  [/^Input should be a valid list/i, () => "Ongeldige lijst."],
  [/^Input should be greater than or equal to (.+)$/i, (m) => `Minimaal ${m[1]}.`],
  [/^Input should be greater than (.+)$/i, (m) => `Moet groter zijn dan ${m[1]}.`],
  [/^Input should be less than or equal to (.+)$/i, (m) => `Maximaal ${m[1]}.`],
  [/^Input should be less than (.+)$/i, (m) => `Moet kleiner zijn dan ${m[1]}.`],
  [/^Input should be True$/i, () => "Moet bevestigd zijn."],
  [/^Input should be False$/i, () => "Moet ‘nee’ zijn."],
  [/^Input should be /i, () => "Kies een geldige waarde."],
  [/^List should have at least (\d+) items?/i, (m) => (m[1] === "1" ? "Voeg minstens één item toe." : `Voeg minstens ${m[1]} items toe.`)],
  [/^List should have at most (\d+) items?/i, (m) => `Maximaal ${m[1]} items.`],
  [/^Extra inputs are not permitted$/i, () => "Onbekend veld."],
];

function capitalize(s: string): string {
  const t = s.trim();
  if (!t) return t;
  const c = t.charAt(0).toUpperCase() + t.slice(1);
  return /[.!?]$/.test(c) ? c : `${c}.`;
}

/** Engelse pydantic-melding → Nederlands. Onbekende meldingen blijven staan (liever eerlijk dan verzonnen). */
export function translateValidation(msg: string): string {
  const t = msg.trim();
  for (const [re, fn] of PATTERNS) {
    const m = re.exec(t);
    if (m) return fn(m);
  }
  return t;
}

/** Serverfouten `{fouten:[{veld, fout}]}` → Errors (zelfde padformaat). */
export function serverErrors(details: Record<string, unknown> | undefined): Errors {
  const out: Errors = {};
  const list = (details?.fouten ?? []) as { veld?: string; fout?: string }[];
  for (const f of Array.isArray(list) ? list : []) {
    const key = f.veld ?? "";
    const msg = translateValidation(String(f.fout ?? ""));
    out[key] = out[key] ? `${out[key]} ${msg}` : msg;
  }
  return out;
}
