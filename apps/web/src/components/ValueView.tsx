import { enumLabel } from "@/lib/decisions";
import type { FieldNode } from "@/lib/schema-form";

/** Leesbare weergave van een ingevulde of gemeten besluitwaarde. */
export function ValueView({ node, value }: { node: FieldNode; value: unknown }) {
  if (value === null || value === undefined || value === "") return <span className="muted">leeg</span>;
  switch (node.kind) {
    case "object": {
      const obj = value as Record<string, unknown>;
      return (
        <dl className="kv">
          {node.fields.map((f) => (
            <div key={f.key} style={{ display: "contents" }}>
              <dt>{f.label}</dt>
              <dd>
                <ValueView node={f} value={obj[f.key]} />
              </dd>
            </div>
          ))}
        </dl>
      );
    }
    case "list": {
      const items = Array.isArray(value) ? value : [];
      if (!items.length) return <span className="muted">geen</span>;
      if (node.item.kind === "object") {
        return (
          <ol className="plain-list">
            {items.map((v, i) => (
              <li key={i} className="card" style={{ padding: 12 }}>
                <ValueView node={node.item} value={v} />
              </li>
            ))}
          </ol>
        );
      }
      return <span>{items.map((v) => (node.item.kind === "enum" ? enumLabel(String(v)) : String(v))).join(", ")}</span>;
    }
    case "boolean":
    case "const":
      return <span>{value === true ? "Ja" : value === false ? "Nee" : String(value)}</span>;
    case "enum":
      return <span>{enumLabel(String(value))}</span>;
    default:
      return <span style={{ overflowWrap: "anywhere" }}>{String(value)}</span>;
  }
}
