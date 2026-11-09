"use client";

import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps, MouseEvent } from "react";
import { cn } from "@/lib/utils";

/**
 * Peil-knop (shadcn Button, new-york, met de codemod uit COMPONENTEN.md §1): altijd ≥ 44 px, Peil-focusring,
 * varianten primair/secundair/stil/gevaar/link. Uitgeschakeld = `aria-disabled` met gestippelde rand en een reden
 * ernaast (nooit `disabled` zonder uitleg: dat haalt de knop uit de tabvolgorde).
 */
export const buttonVariants = cva(
  "inline-flex min-h-touch min-w-touch cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-transparent px-4 py-2 text-base leading-5 font-semibold no-underline transition-colors select-none [&_svg]:size-5 [&_svg]:shrink-0 aria-disabled:cursor-not-allowed aria-disabled:border-dashed aria-disabled:border-border-strong aria-disabled:bg-muted aria-disabled:text-disabled-foreground aria-disabled:hover:bg-muted aria-busy:cursor-progress",
  {
    variants: {
      variant: {
        primair: "bg-primary text-primary-foreground hover:bg-primary-hover",
        secundair: "border-border-strong bg-card text-foreground hover:bg-accent",
        stil: "bg-transparent text-foreground hover:bg-accent",
        gevaar: "bg-destructive text-destructive-foreground hover:bg-destructive-hover",
        link: "border-0 bg-transparent px-1 text-link underline underline-offset-3 hover:decoration-2",
      },
      size: {
        standaard: "",
        klein: "px-3 text-sm",
        icoon: "size-touch px-0",
      },
      blok: { true: "w-full justify-between", false: "" },
    },
    defaultVariants: { variant: "secundair", size: "standaard", blok: false },
  },
);

export interface ButtonProps extends ComponentProps<"button">, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  /** Zichtbaar maar niet bruikbaar; geef de reden mee via aria-describedby. */
  uit?: boolean;
  bezig?: boolean;
}

export function Button({ className, variant, size, blok, asChild, uit, bezig, onClick, type, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  const blocked = Boolean(uit || bezig);
  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, blok }), className)}
      type={asChild ? undefined : (type ?? "button")}
      aria-disabled={uit ? true : undefined}
      aria-busy={bezig ? true : undefined}
      onClick={(e: MouseEvent<HTMLButtonElement>) => {
        if (blocked) {
          e.preventDefault();
          return;
        }
        onClick?.(e);
      }}
      {...props}
    />
  );
}
