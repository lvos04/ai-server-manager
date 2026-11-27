// De image bevat alleen de routegegevens. De vier manifesten staan bij gebruik in een privémap van de webgebruiker.
import { createHmac } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

export const runtimeMap = "/run/hub-web";
export const sjabloon = "hub-prerender.json";
export const manifesten = [
  "prerender-manifest.json", "server/preview-props.json",
  "server/server-reference-manifest.json", "server/server-reference-manifest.js",
];

export function schrijfWebmanifesten(nextMap, runtime, sleutel) {
  if (sleutel.length !== 32) throw new Error("Ongeldige installatiesleutel voor de webserver");
  const afleiden = (doel) => createHmac("sha256", sleutel).update(doel).digest();
  const preview = {
    previewModeId: afleiden("preview-id").subarray(0, 16).toString("hex"),
    previewModeSigningKey: afleiden("preview-ondertekening").toString("hex"),
    previewModeEncryptionKey: afleiden("preview-versleuteling").toString("hex"),
  };
  const acties = { node: {}, edge: {}, encryptionKey: afleiden("server-actions").toString("base64") };
  const prerender = JSON.parse(readFileSync(path.join(nextMap, sjabloon), "utf8"));
  const inhoud = [
    JSON.stringify({ ...prerender, preview }), JSON.stringify(preview),
    JSON.stringify(acties), "self.__RSC_SERVER_MANIFEST=" + JSON.stringify(JSON.stringify(acties)),
  ];
  // Eén webproces per container. Alle vier zijn geschreven voordat Next de eerste aanvraag kan behandelen.
  for (const [i, naam] of manifesten.entries()) {
    writeFileSync(path.join(runtime, path.basename(naam)), inhoud[i], { mode: 0o600 });
  }
  return acties.encryptionKey;
}
