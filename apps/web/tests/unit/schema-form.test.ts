import { describe as suite, expect, it } from "vitest";
import schemas from "./fixtures/decision-schemas.json";
import {
  describe,
  emptyDraft,
  fromDraft,
  serverErrors,
  setAt,
  toDraft,
  translateValidation,
  type Draft,
  type FieldNode,
} from "@/lib/schema-form";
import type { JsonSchema } from "@/lib/types";

const all = schemas as unknown as Record<string, JsonSchema>;
const node = (id: string): FieldNode => describe(all[id] as JsonSchema, all[id] as JsonSchema);

function leaves(d: Draft): Draft[] {
  if (Array.isArray(d)) return d.flatMap(leaves);
  if (d && typeof d === "object") return Object.values(d).flatMap(leaves);
  return [d];
}

suite("schemaformulier voor alle besluiten D01–D18", () => {
  it("ondersteunt elk schema uit de catalogus", () => {
    expect(Object.keys(all)).toHaveLength(18);
    for (const [id, schema] of Object.entries(all)) {
      const n = describe(schema, schema);
      expect(n.kind, id).toBe("object");
    }
  });

  it("start altijd leeg: geen voorbeeldwaarden, geen vooraf gekozen ja/nee", () => {
    for (const id of Object.keys(all)) {
      const d = emptyDraft(node(id));
      for (const leaf of leaves(d)) expect(leaf === "" || leaf === null, `${id}: ${String(leaf)}`).toBe(true);
    }
  });

  it("leeg opslaan geeft fouten voor verplichte velden (D03: nas_adres, D02: lijsten)", () => {
    expect(fromDraft(node("D03"), emptyDraft(node("D03"))).errors).toEqual({ nas_adres: "Verplicht veld." });
    const e2 = fromDraft(node("D02"), emptyDraft(node("D02"))).errors;
    expect(e2.pools).toBe("Voeg minstens één item toe.");
    expect(e2.appdata_datasets).toBe("Voeg minstens één item toe.");
    expect(e2.media_datasets).toBeUndefined();
  });

  it("zet optionele velden op null of een lege lijst en getallen om (ook met komma)", () => {
    const n = node("D03");
    const d = setAt(setAt(emptyDraft(n), ["nas_adres"], "nas.lan"), ["https_poort"], "8443");
    const { value, errors } = fromDraft(n, d);
    expect(errors).toEqual({});
    expect(value).toEqual({ nas_adres: "nas.lan", https_poort: 8443, hostnamen: [], vpn: null, tunnel: null, open_poorten_firewall: [] });
    const n16 = node("D16") as Extract<FieldNode, { kind: "object" }>;
    const list = n16.fields[0] as Extract<FieldNode, { kind: "list" }>;
    const item = setAt(setAt(setAt(emptyDraft(list.item), ["app_id"], "hub"), ["rpo_uren"], "1,5"), ["rto_uren"], "4");
    const r16 = fromDraft(n16, { per_app: [item] });
    expect(r16.errors).toEqual({});
    expect(r16.value).toEqual({ per_app: [{ app_id: "hub", rpo_uren: 1.5, rto_uren: 4 }] });
  });

  it("controleert grenzen, gehele getallen, patronen en keuzes", () => {
    const n = node("D03");
    expect(fromDraft(n, { nas_adres: "x", https_poort: "70000" }).errors.https_poort).toBe("Maximaal 65535.");
    expect(fromDraft(n, { nas_adres: "x", https_poort: "1.5" }).errors.https_poort).toBe("Vul een geheel getal in.");
    expect(fromDraft(n, { nas_adres: "x", https_poort: "abc" }).errors.https_poort).toBe("Vul een geheel getal in.");
    const n16 = node("D16");
    const r = fromDraft(n16, { per_app: [{ app_id: "Fout!", rpo_uren: "0", rto_uren: "2" }] });
    expect(r.errors["per_app.0.app_id"]).toBe("Ongeldig formaat.");
    expect(r.errors["per_app.0.rpo_uren"]).toBe("Moet groter zijn dan 0.");
    const n4 = node("D04");
    expect(fromDraft(n4, emptyDraft(n4)).errors.methode).toBe("Maak een keuze.");
    expect(fromDraft(n4, emptyDraft(n4)).errors.versleuteld).toBe("Kies ja of nee.");
  });

  it("const true (harde stop) moet bevestigd worden; const false is vast", () => {
    const n9 = node("D09");
    const r = fromDraft(n9, emptyDraft(n9));
    expect(r.errors.harde_stop).toBe("Bevestig dit om verder te gaan.");
    expect((r.value as Record<string, unknown>).overage_toegestaan).toBe(false);
    const ok = fromDraft(n9, { account_gekoppeld: false, inbegrepen_maandbudget: "", harde_stop: true, overage_toegestaan: null });
    expect(ok.errors).toEqual({});
  });

  it("nullable ja/nee mag leeg blijven (onbekend)", () => {
    const n6 = node("D06");
    const d = toDraft(n6, { pools: [{ naam: "p", status: "ONLINE", gezond: true }], smart_ok: null });
    const r = fromDraft(n6, d);
    expect(r.errors).toEqual({});
    expect((r.value as Record<string, unknown>).smart_ok).toBeNull();
  });

  it("toDraft ↔ fromDraft behoudt een ingevulde waarde", () => {
    const n = node("D08");
    const v = { gpus: [{ rol: "a310", pci_slot: "s1", render_node: "/dev/dri/renderD128" }], qsv_apps: ["x"] };
    expect(fromDraft(n, toDraft(n, v))).toEqual({ value: v, errors: {} });
  });

  it("setAt is onveranderlijk", () => {
    const before = { a: ["1", "2"] } as Draft;
    const after = setAt(before, ["a", 1], "x");
    expect(before).toEqual({ a: ["1", "2"] });
    expect(after).toEqual({ a: ["1", "x"] });
  });
});

suite("vertaling van servervalidatie", () => {
  it.each([
    ["Field required", "Verplicht veld."],
    ["Value error, lijkt een plaatshouder/voorbeeldwaarde; vul de echte waarde in", "Lijkt een plaatshouder/voorbeeldwaarde; vul de echte waarde in."],
    ["String should have at least 1 character", "Minstens 1 teken."],
    ["String should match pattern '^x$'", "Ongeldig formaat."],
    ["Input should be a valid integer, unable to parse string as an integer", "Vul een geheel getal in."],
    ["Input should be greater than 0", "Moet groter zijn dan 0."],
    ["Input should be less than or equal to 65535", "Maximaal 65535."],
    ["Input should be True", "Moet bevestigd zijn."],
    ["Input should be 'a310', 'uhd770' or 'anders'", "Kies een geldige waarde."],
    ["List should have at least 1 item after validation, not 0", "Voeg minstens één item toe."],
    ["Extra inputs are not permitted", "Onbekend veld."],
  ])("%s → %s", (input, out) => {
    expect(translateValidation(input)).toBe(out);
  });

  it("onbekende meldingen blijven ongewijzigd (niets verzinnen)", () => {
    expect(translateValidation("iets heel anders")).toBe("iets heel anders");
  });

  it("serverErrors koppelt fouten per veldpad", () => {
    expect(
      serverErrors({ fouten: [{ veld: "taken.0", fout: "Value error, lijkt een plaatshouder" }, { veld: "", fout: "Value error, dataset hoort niet bij pool" }] }),
    ).toEqual({ "taken.0": "Lijkt een plaatshouder.", "": "Dataset hoort niet bij pool." });
    expect(serverErrors(undefined)).toEqual({});
  });
});
