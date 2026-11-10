"use client";

import * as AD from "@radix-ui/react-alert-dialog";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { buttonVariants } from "./button";

/** Bevestiging (shadcn AlertDialog) in Peil: vaste laag z-overlay, geen opacity-truc op het vlak. */
export function BevestigDialoog({
  open,
  onOpenChange,
  titel,
  children,
  bevestig,
  annuleer = "Annuleren",
  onBevestig,
  gevaar,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  titel: string;
  children: ReactNode;
  bevestig: string;
  annuleer?: string;
  onBevestig: () => void;
  gevaar?: boolean;
}) {
  return (
    <AD.Root open={open} onOpenChange={onOpenChange}>
      <AD.Portal>
        <AD.Overlay className="fixed inset-0 z-overlay bg-black/50" />
        <AD.Content
          className={cn(
            "fixed top-1/2 left-1/2 z-overlay flex w-[min(32rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-xl border border-border-strong bg-popover p-6 text-popover-foreground shadow-lg",
          )}
        >
          <AD.Title className="text-xl font-bold">{titel}</AD.Title>
          <AD.Description asChild>
            <div className="flex flex-col gap-2">{children}</div>
          </AD.Description>
          <div className="flex flex-wrap justify-end gap-2">
            <AD.Cancel className={buttonVariants({ variant: "secundair" })}>{annuleer}</AD.Cancel>
            <AD.Action className={buttonVariants({ variant: gevaar ? "gevaar" : "primair" })} onClick={onBevestig}>
              {bevestig}
            </AD.Action>
          </div>
        </AD.Content>
      </AD.Portal>
    </AD.Root>
  );
}

export type BevestigDialoogProps = ComponentProps<typeof BevestigDialoog>;
