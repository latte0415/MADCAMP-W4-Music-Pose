import type { EventPoint } from "../types/event";
import type { EnergyEvent, EnergyJsonData } from "../types/energyEvent";
import type { ClarityEvent, ClarityJsonData } from "../types/clarityEvent";
import type { TemporalEvent, TemporalJsonData } from "../types/temporalEvent";

const DEFAULT_POINT_COLOR = "#5a9fd4";

/** 02_clarity 형식(metadata + attack_time_ms, clarity_score) → Clarity 데이터 반환, 아니면 null */
export function parseClarityJson(data: unknown): ClarityJsonData | null {
  if (!data || typeof data !== "object") return null;
  const obj = data as Record<string, unknown>;
  const metaRaw = obj.metadata ?? obj.meta;
  if (metaRaw == null || typeof metaRaw !== "object" || !Array.isArray(obj.events)) return null;
  const rawEvents = obj.events as Record<string, unknown>[];
  const hasClarity = rawEvents.some(
    (e) => e && typeof e === "object" && ("attack_time_ms" in e || "clarity_score" in e)
  );
  if (!hasClarity) return null;

  const m = metaRaw as Record<string, unknown>;
  const events: ClarityEvent[] = rawEvents
    .filter((item): item is Record<string, unknown> => item != null && typeof item === "object")
    .map((item) => ({
      t: Number(item.time ?? item.t ?? 0),
      strength: Math.min(1, Math.max(0, Number(item.strength ?? 0))),
      attack_time_ms: Number(item.attack_time_ms ?? 0),
      clarity_score: Number(item.clarity_score ?? 0),
    }));

  return {
    events,
    meta: {
      source: String(m.source ?? ""),
      sr: Number(m.sr ?? 22050),
      hop_length: Number(m.hop_length ?? 256),
      bpm: Number(m.bpm ?? 0),
      total_events: Number(m.total_events ?? events.length),
    },
  };
}

/** 03_temporal 형식(metadata + grid_align_score, temporal_score) → Temporal 데이터 반환, 아니면 null */
export function parseTemporalJson(data: unknown): TemporalJsonData | null {
  if (!data || typeof data !== "object") return null;
  const obj = data as Record<string, unknown>;
  const metaRaw = obj.metadata ?? obj.meta;
  if (metaRaw == null || typeof metaRaw !== "object" || !Array.isArray(obj.events)) return null;
  const rawEvents = obj.events as Record<string, unknown>[];
  const hasTemporal = rawEvents.some(
    (e) => e && typeof e === "object" && ("grid_align_score" in e || "temporal_score" in e)
  );
  if (!hasTemporal) return null;

  const m = metaRaw as Record<string, unknown>;
  const events: TemporalEvent[] = rawEvents
    .filter((item): item is Record<string, unknown> => item != null && typeof item === "object")
    .map((item) => {
      const ev: TemporalEvent = {
        index: Number(item.index ?? 0),
        time: Number(item.time ?? item.t ?? 0),
        frame: Number(item.frame ?? 0),
        strength: Number(item.strength ?? 0),
        grid_align_score: Number(item.grid_align_score ?? 0),
        repetition_score: Number(item.repetition_score ?? 0),
        temporal_score: Number(item.temporal_score ?? 0),
      };
      if (item.ioi_prev != null) ev.ioi_prev = Number(item.ioi_prev);
      if (item.ioi_next != null) ev.ioi_next = Number(item.ioi_next);
      return ev;
    });

  return {
    events,
    meta: {
      source: String(m.source ?? ""),
      sr: Number(m.sr ?? 22050),
      duration_sec: Number(m.duration_sec ?? 0),
      hop_length: Number(m.hop_length ?? 256),
      bpm: Number(m.bpm ?? 0),
      bpm_dynamic_used: Boolean(m.bpm_dynamic_used ?? false),
      total_events: Number(m.total_events ?? events.length),
    },
  };
}

/** 04 형식(energy_rms_min 있음) → 전체 에너지 데이터 반환, 아니면 null */
export function parseEnergyJson(data: unknown): EnergyJsonData | null {
  if (!data || typeof data !== "object") return null;
  const obj = data as Record<string, unknown>;
  if (obj.energy_rms_min == null || !Array.isArray(obj.events)) return null;

  const raw = (obj.events as Record<string, unknown>[])
    .filter((item): item is Record<string, unknown> => item != null && typeof item === "object")
    .map((item) => ({
      t: Number(item.t ?? 0),
      strength: Math.min(1, Math.max(0, Number(item.strength ?? 0.7))),
      texture: Math.min(1, Math.max(0, Number(item.texture ?? 0.5))),
      color: typeof item.color === "string" && item.color ? item.color : DEFAULT_POINT_COLOR,
      rms: Number(item.rms ?? 0),
      e_norm: Number(item.e_norm ?? item.strength ?? 0.7),
      band_low: Number(item.band_low ?? 0),
      band_mid: Number(item.band_mid ?? 0),
      band_high: Number(item.band_high ?? 0),
    }));

  const sorted = [...raw.map((e) => e.strength)].sort((a, b) => a - b);
  const t33 = sorted[Math.floor(sorted.length * 0.33)] ?? 0;
  const t66 = sorted[Math.floor(sorted.length * 0.66)] ?? 1;

  const events: EnergyEvent[] = raw.map((e) => ({
    ...e,
    layer: e.strength >= t66 ? "강함" : e.strength >= t33 ? "중간" : "약함",
  }));

  return {
    events,
    meta: {
      source: String(obj.source ?? ""),
      sr: Number(obj.sr ?? 22050),
      duration_sec: Number(obj.duration_sec ?? 0),
      energy_rms_min: Number(obj.energy_rms_min ?? 0),
      energy_rms_max: Number(obj.energy_rms_max ?? 1),
    },
  };
}

/**
 * json_spec.md 기반 — 노트북별 JSON 형식 → EventPoint[] 변환
 *
 * 수용 형식 (우선순위):
 * 1. onset_beats.json (01_explore): onset_times_sec, beat_times_sec, drum_onset_times_sec
 * 2. onset_events.json (03_visualize_point): events[] (t, strength, texture, color, layer)
 * 3. events[] 래퍼
 * 4. 배열 직접 [{ t, strength?, color?, layer? }]
 */
export function parseEventsFromJson(data: unknown): EventPoint[] {
  if (!data || typeof data !== "object") return [];

  const obj = data as Record<string, unknown>;

  // 1. 01_explore → onset_beats.json (강함/중간/약함에 매핑: drum_onset→강함, beat→중간, onset→약함)
  if ("onset_times_sec" in obj || "beat_times_sec" in obj || "drum_onset_times_sec" in obj) {
    const events: EventPoint[] = [];
    if (Array.isArray(obj.onset_times_sec)) {
      (obj.onset_times_sec as number[]).forEach((t) => {
        events.push({ t: Number(t), strength: 0.7, color: DEFAULT_POINT_COLOR, layer: "약함" });
      });
    }
    if (Array.isArray(obj.beat_times_sec)) {
      (obj.beat_times_sec as number[]).forEach((t) => {
        events.push({ t: Number(t), strength: 0.6, color: DEFAULT_POINT_COLOR, layer: "중간" });
      });
    }
    if (Array.isArray(obj.drum_onset_times_sec)) {
      (obj.drum_onset_times_sec as number[]).forEach((t) => {
        events.push({ t: Number(t), strength: 0.8, color: DEFAULT_POINT_COLOR, layer: "강함" });
      });
    }
    return events;
  }

  // 2, 3. 03_visualize_point / 04_layered_onset → onset_events.json 또는 events[] 래퍼
  if (Array.isArray(obj.events)) {
    const events = (obj.events as Record<string, unknown>[])
      .filter((item): item is Record<string, unknown> => item != null && typeof item === "object")
      .map((item) => normalizeEvent(item));

    // 03/04 형식: strength 기준 강함/중간/약함 tertile 할당
    if (events.length > 0) {
      const strengths = events.map((e) => e.strength);
      const sorted = [...strengths].sort((a, b) => a - b);
      const t33 = sorted[Math.floor(sorted.length * 0.33)] ?? 0;
      const t66 = sorted[Math.floor(sorted.length * 0.66)] ?? 1;
      events.forEach((e, i) => {
        const v = strengths[i];
        if (v >= t66) e.layer = "강함";
        else if (v >= t33) e.layer = "중간";
        else e.layer = "약함";
      });
    }
    return events;
  }

  // 4. 배열 직접 — strength tertile로 강함/중간/약함 할당
  if (Array.isArray(data)) {
    const events = (data as Record<string, unknown>[])
      .filter((item): item is Record<string, unknown> => item != null && typeof item === "object")
      .map((item) => normalizeEvent(item));
    if (events.length > 0) {
      const strengths = events.map((e) => e.strength);
      const sorted = [...strengths].sort((a, b) => a - b);
      const t33 = sorted[Math.floor(sorted.length * 0.33)] ?? 0;
      const t66 = sorted[Math.floor(sorted.length * 0.66)] ?? 1;
      events.forEach((e, i) => {
        const v = strengths[i];
        if (v >= t66) e.layer = "강함";
        else if (v >= t33) e.layer = "중간";
        else e.layer = "약함";
      });
    }
    return events;
  }

  return [];
}

function normalizeEvent(item: Record<string, unknown>): EventPoint {
  const t = Number(item.t ?? item.time ?? 0);
  const strength = Math.min(1, Math.max(0, Number(item.strength ?? 0.7)));
  const textureRaw = Number(item.texture);
  const texture = Number.isFinite(textureRaw)
    ? Math.min(1, Math.max(0, textureRaw))
    : undefined;
  const color =
    typeof item.color === "string" && item.color ? item.color : DEFAULT_POINT_COLOR;
  const layer = typeof item.layer === "string" ? item.layer : "default";
  return { t, strength, texture, color, layer };
}
