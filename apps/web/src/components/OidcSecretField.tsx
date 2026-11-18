import type { InputHTMLAttributes } from "react";
import { Field } from "@/components/Field";

export function OidcSecretField({ https, ingesteld, laatste4, ...input }: InputHTMLAttributes<HTMLInputElement> & { https: boolean; ingesteld: boolean; laatste4: string | null }) {
  if (!https) return <p className="help">Het clientgeheim invoeren kan alleen via HTTPS. Open de Hub via een vertrouwde HTTPS-verbinding.</p>;
  return (
    <Field id="sso-geheim" label={ingesteld ? "Clientgeheim vervangen (optioneel)" : "Clientgeheim"}
      help={ingesteld ? `Ingesteld: ••••${laatste4 ?? ""}. Leeg laten = niet wijzigen.` : "Wordt versleuteld opgeslagen; je ziet daarna alleen de laatste 4 tekens."}>
      {(a) => <input {...a} {...input} type="password" autoComplete="new-password" />}
    </Field>
  );
}
