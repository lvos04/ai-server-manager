"use client";

import * as D from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { buttonVariants } from "./button";

/** Sheet van onder (mobiel), shadcn Sheet op Radix Dialog: focusval, Esc sluit, focus terug naar de opener. */
export function Sheet({
  open,
  onOpenChange,
  titel,
  children,
  testId,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  titel: string;
  children: ReactNode;
  testId?: string;
}) {
  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-overlay bg-black/60" />
        <D.Content
          data-testid={testId}
          className="fixed inset-x-0 bottom-0 z-overlay flex max-h-[85dvh] flex-col gap-3 overflow-y-auto rounded-t-xl border-t border-border-strong bg-popover p-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))] text-popover-foreground shadow-lg"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between gap-2">
            <D.Title className="text-xl font-bold">{titel}</D.Title>
            <D.Close className={buttonVariants({ variant: "stil", size: "icoon" })} aria-label="Sluiten">
              <X aria-hidden="true" />
            </D.Close>
          </div>
          {children}
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}
