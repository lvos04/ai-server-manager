export function huisMeting(observedAt = new Date().toISOString()) {
  return {
    observed_at: observedAt,
    instellingen: { safe_mode: true, observed_at: observedAt, link: "https://huis.example" },
    laatste_backup: { age_h: 2.5, observed_at: observedAt },
    woningen: [{
      woning: { id: "woning", name: "Proefwoning" },
      zones: [{
        id: "woonkamer",
        name: "Woonkamer",
        target_c: 21,
        temperature: { value: 20.5, unit: "°C", at: observedAt, quality: "measured", max_age_s: 300, stale: false },
      }, {
        id: "slaapkamer",
        name: "Slaapkamer",
        target_c: null,
        temperature: { value: null, unit: "°C", at: observedAt, quality: "measured", max_age_s: 300, stale: true },
      }],
      licht: { groups: [
        { id: "plafond", name: "Plafondlamp", on: true, reachable: true },
        { id: "leeslamp", name: "Leeslamp", on: false, reachable: true },
      ] },
      apparaten: [{ id: "plafond", kind: "light_group", online: true, last_seen: observedAt },
        { id: "leeslamp", kind: "light_group", online: true, last_seen: observedAt }],
      meldingen: { observed_at: observedAt, items: [{ id: "melding", severity: "warn", created_at: observedAt }], open: 1, begrensd: false },
    }],
  };
}
