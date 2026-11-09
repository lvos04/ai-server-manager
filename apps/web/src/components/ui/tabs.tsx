"use client";

import * as TabsPrimitive from "@radix-ui/react-tabs";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/** Peil-tabs (COMPONENTEN §21): telefoon omlopende knoppen, ≥ md een rij met onderstreping; maximaal één tabrij. */
export const Tabs = TabsPrimitive.Root;

export function TabsList({ className, ...props }: ComponentProps<typeof TabsPrimitive.List>) {
  return <TabsPrimitive.List className={cn("flex flex-wrap gap-2 md:gap-1 md:border-b-2 md:border-border", className)} {...props} />;
}

export function TabsTrigger({ className, ...props }: ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "inline-flex min-h-touch cursor-pointer items-center gap-2 rounded-lg border border-border-strong bg-card px-3.5 font-semibold text-foreground [&_svg]:size-5",
        "aria-selected:border-foreground aria-selected:bg-foreground aria-selected:text-background",
        "md:-mb-0.5 md:rounded-none md:border-0 md:border-b-4 md:border-transparent md:bg-transparent md:hover:bg-accent md:aria-selected:border-primary md:aria-selected:bg-transparent md:aria-selected:text-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({ className, ...props }: ComponentProps<typeof TabsPrimitive.Content>) {
  return <TabsPrimitive.Content className={cn("mt-4 flex flex-col gap-4", className)} {...props} />;
}
