# 파이프라인 — 데이터 흐름·스크립트 실행 순서

전체 흐름과 엔트리 스크립트, engine.onset 연동을 정리합니다.

---

## 1. 전체 흐름

```
오디오 파일
    → Step 1 탐색 (01_explore)        → onset_beats.json
    → Step 2 스템 분리 (02_split_stem) → stems/htdemucs/{트랙}/drums|bass|vocals|other.wav
    → Step 3 시각화 (03_visualize_point) → onset_events.json
    → 레이어드 익스포트 (01_energy ~ 05_context) → onset_events_energy|clarity|temporal|spectral|context.json
    → 레이어 통합 (06_layered_export)  → onset_events_layered.json
    → Web (JsonUploader, parseEvents) → 파형 위 이벤트/레이어 표시
```

---

## 2. 스크립트·엔트리 (실제 경로)

| 스크립트 | 경로 | 역할 | 출력 JSON |
|----------|------|------|-----------|
| 01_explore | `audio_engine/scripts/01_basic_test/01_explore.py` | Onset/Beat 검출 | `onset_beats.json` |
| 02_split_stem | `audio_engine/scripts/01_basic_test/02_split_stem.py` | Demucs 스템 분리 | (WAV 4개) |
| 03_visualize_point | `audio_engine/scripts/01_basic_test/03_visualize_point.py` | 세기·질감 시각화용 JSON | `onset_events.json` |
| 01_energy | `audio_engine/scripts/02_layered_onset_export/01_energy.py` | Energy(RMS·대역) | `onset_events_energy.json` |
| 02_clarity | `audio_engine/scripts/02_layered_onset_export/02_clarity.py` | Clarity(attack time) | `onset_events_clarity.json` |
| 03_temporal | `audio_engine/scripts/02_layered_onset_export/03_temporal.py` | Temporal(그리드·반복) | `onset_events_temporal.json` |
| 04_spectral | `audio_engine/scripts/02_layered_onset_export/04_spectral.py` | Spectral(focus) | `onset_events_spectral.json` |
| 05_context | `audio_engine/scripts/02_layered_onset_export/05_context.py` | Context(dependency) | `onset_events_context.json` |
| **06_layered_export** | `audio_engine/scripts/02_layered_onset_export/06_layered_export.py` | 5개 피처 + P0/P1/P2 할당 | `onset_events_layered.json` |

02_layered_onset_export 스크립트는 모두 `audio_engine.engine.onset`만 사용합니다.

---

## 3. 06_layered_export 흐름 (실제 코드)

1. `build_context(audio_path, include_temporal=True)` → `OnsetContext`
2. `compute_energy(ctx)`, `compute_clarity(ctx)`, `compute_temporal(ctx)`, `compute_spectral(ctx)`, `compute_context_dependency(ctx)` → 5개 지표
3. `compute_layer_scores(metrics)` → S0, S1, S2
4. `assign_layer(S0, S1, S2)` → layer_indices (0=P0, 1=P1, 2=P2)
5. `apply_layer_floor(layer_indices, S0, S1, S2, min_p0_ratio=0.20, min_p0_p1_ratio=0.40)` → 비율 보정
6. `write_layered_json(ctx, metrics, layer_indices, json_path, ...)` → `onset_events_layered.json` + `web/public` 복사

---

## 4. 샘플 오디오·출력 위치

- **입력 예시**: `audio_engine/samples/stems/htdemucs/sample_ropes_short/drums.wav`
- **출력**: `audio_engine/samples/onset_events_*.json`, `onset_events_layered.json`
- **웹 복사**: `web/public/` (동일 파일명)
