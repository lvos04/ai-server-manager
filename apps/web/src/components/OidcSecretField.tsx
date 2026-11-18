"use client";

import { useEffect, useRef, type RefObject } from "react";
import { Field } from "@/components/Field";

export function takeOidcSecret(input: HTMLInputElement | null): string {
  const value = input?.value ?? "";
  if (input) input.value = "";
  return value;
}

export function watchOidcSecret(input: HTMLInputElement | null, target: EventTarget): () => void {
  const clear = () => { takeOidcSecret(input); };
  target.addEventListener("pagehide", clear);
  target.addEventListener("pageshow", clear);
  return () => {
    clear();
    target.removeEventListener("pagehide", clear);
    target.removeEventListener("pageshow", clear);
  };
}

export function OidcSecretField({ https, ingesteld, laatste4, inputRef }: { https: boolean; ingesteld: boolean; laatste4: string | null; inputRef?: RefObject<HTMLInputElement | null> }) {
  const ownRef = useRef<HTMLInputElement>(null);
  const fieldRef = inputRef ?? ownRef;
  useEffect(() => watchOidcSecret(fieldRef.current, window), [fieldRef]);
  if (!https) return <p className="help">Het clientgeheim invoeren kan alleen via HTTPS. Open de Hub via een vertrouwde HTTPS-verbinding.</p>;
  return (
    <Field id="sso-geheim" label={ingesteld ? "Clientgeheim vervangen (optioneel)" : "Clientgeheim"}
      help={ingesteld ? `Ingesteld: ••••${laatste4 ?? ""}. Leeg laten = niet wijzigen.` : "Wordt versleuteld opgeslagen; je ziet daarna alleen de laatste 4 tekens."}>
      {(a) => <input {...a} ref={fieldRef} type="password" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" spellCheck={false} autoCapitalize="none" />}
    </Field>
  );
}
