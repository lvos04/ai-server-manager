import type { StatusView, Tone } from "@/lib/status";

const SYMBOL: Record<Tone, string> = { ok: "✓", info: "i", warn: "!", bad: "✕", unknown: "?", neutral: "–" };

/** Status met symbool én tekst (nooit alleen kleur). */
export function StatusBadge({ view, testId }: { view: StatusView; testId?: string }) {
  return (
    <span className={`badge tone-${view.tone}`} data-tone={view.tone} data-testid={testId}>
      <span className="sym" aria-hidden="true">
        {SYMBOL[view.tone]}
      </span>
      {view.label}
    </span>
  );
}
