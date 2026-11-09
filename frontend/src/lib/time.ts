/** 75 → "1:15", 3725 → "1:02:05". Negative and NaN become 0. */
export function formatTime(sec: number): string {
  const s0 = Number.isFinite(sec) ? Math.max(0, Math.floor(sec)) : 0;
  const h = Math.floor(s0 / 3600);
  const m = Math.floor((s0 % 3600) / 60);
  const s = s0 % 60;
  return (h ? h + ":" + String(m).padStart(2, "0") : String(m)) + ":" + String(s).padStart(2, "0");
}

/** "1:02:05", "2:30", "90", "1h2m5s" → seconds; null when it is not a time. */
export function parseTime(v: string | null | undefined): number | null {
  if (v == null) return null;
  const s = String(v).trim();
  if (!s) return null;
  if (/^\d+(\.\d+)?$/.test(s)) return Number(s);
  if (/^\d+(:\d{1,2}){1,2}$/.test(s)) return s.split(":").reduce((acc, p) => acc * 60 + Number(p), 0);
  const m = s.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/i);
  if (m && (m[1] || m[2] || m[3])) return Number(m[1] || 0) * 3600 + Number(m[2] || 0) * 60 + Number(m[3] || 0);
  return null;
}

/** Byte sizes with the unit names of the current UI language. */
export function formatSize(bytes: number, units: { kb: string; mb: string; gb: string }): string {
  const b = Math.max(0, Number(bytes) || 0);
  if (b >= 1e9) return (b / 1e9).toFixed(1) + " " + units.gb;
  if (b >= 1e6) return (b / 1e6).toFixed(1) + " " + units.mb;
  return Math.max(1, Math.ceil(b / 1e3)) + " " + units.kb;
}
