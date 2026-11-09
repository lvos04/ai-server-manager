export function Loading({ text = "Laden…" }: { text?: string }) {
  return (
    <p className="muted" role="status" aria-live="polite" data-testid="loading">
      {text}
    </p>
  );
}
