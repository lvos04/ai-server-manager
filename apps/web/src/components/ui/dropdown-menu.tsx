"use client";

import * as DM from "@radix-ui/react-dropdown-menu";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/** Gebruikersmenu (shadcn DropdownMenu) in Peil: items ≥ 44 px, vaste laag z-overlay. */
export const Menu = DM.Root;
export const MenuTrigger = DM.Trigger;
export const MenuPortal = DM.Portal;

export function MenuContent({ className, ...props }: ComponentProps<typeof DM.Content>) {
  return (
    <DM.Content
      sideOffset={6}
      align="end"
      className={cn("z-overlay flex min-w-56 flex-col gap-1 rounded-lg border border-border-strong bg-popover p-1.5 text-popover-foreground shadow-md", className)}
      {...props}
    />
  );
}

export function MenuItem({ className, ...props }: ComponentProps<typeof DM.Item>) {
  return (
    <DM.Item
      className={cn(
        "flex min-h-touch cursor-pointer items-center gap-2 rounded-md px-3 font-semibold text-foreground no-underline outline-none data-[highlighted]:bg-accent [&_svg]:size-5 [&_svg]:text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function MenuLabel({ className, ...props }: ComponentProps<typeof DM.Label>) {
  return <DM.Label className={cn("px-3 py-2 text-sm text-muted-foreground", className)} {...props} />;
}

export function MenuSeparator({ className, ...props }: ComponentProps<typeof DM.Separator>) {
  return <DM.Separator className={cn("my-1 h-px bg-border", className)} {...props} />;
}
