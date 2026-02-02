# docs — 문서 구조

---

## 1. 기록해야 할 정보 (전부 정리)

| 구분 | 기록할 내용 |
|------|-------------|
| **아키텍처** | onset 모듈 L1~L6 레이어, 파일 경로, **공개 API 목록**(`__init__.py` 기준), 상수(hop_length, BAND_HZ 등), OnsetContext 필드, 검증 방법 |
| **파이프라인** | 전체 흐름(탐색→스템→시각화→레이어드 익스포트→웹), 스크립트 01~06 실행 순서, 엔트리 포인트와 engine.onset 연동, `06_layered_export.py` → `onset_events_layered.json` |
| **사양(spec)** | JSON 파일별 스키마(onset_beats, onset_events, onset_events_energy/clarity/temporal/spectral/context, **onset_events_layered**), Web 수용 형식 |
| **설계(design)** | 5개 지표(Energy, Clarity, Temporal, Spectral, Context) 개념·점수화, P0/P1/P2 방향, **실제 스코어 공식**(가중치), `normalize_metrics_per_track`, `apply_layer_floor` 비율 |
| **계획(plans)** | 같은 비트·다른 값 안정화(backtrack, round, 가변 윈도우, 로컬 리파인, 구간 안정형 등) |
| **온보딩** | 환경(Python, 의존성), 실행 순서, 샘플 오디오 위치, 검증 한 번에 실행할 명령 |
| **진행(progress)** | 파이프라인 다이어그램, 진행 현황, 점수 해석 가이드, 값 가공 요약, 파일별 역할 |

---

## 2. 분류 제안

| 분류 | 용도 | 문서 |
|------|------|------|
| **architecture** | 코드·모듈 구조, 공개 API, 검증 | [onset_module.md](onset_module.md) |
| **pipeline** | 데이터 흐름, 스크립트 실행 순서 | [pipeline.md](pipeline.md) |
| **spec** | 데이터·출력 형식 사양 | [json_spec.md](json_spec.md) |
| **design** | 설계 결정(레이어링, 점수, 요소) | [layering.md](layering.md) |
| **plans** | 계획·개선안 | [onset_stability.md](onset_stability.md) |
| **dev_onboarding** | 새 개발자 환경·실행·검증 | [dev_onboarding.md](dev_onboarding.md) |
| **progress** | 진행 상황·값 가공·점수 해석 | [progress.md](progress.md) |

---

## 3. 목차 (빠른 참조)

- **모듈 구조·API·검증** → [onset_module.md](onset_module.md)
- **전체 흐름·스크립트 01~06** → [pipeline.md](pipeline.md)
- **JSON 필드·Web 형식** → [json_spec.md](json_spec.md)
- **레이어링·점수 공식** → [layering.md](layering.md)
- **안정화 계획** → [onset_stability.md](onset_stability.md)
- **처음 셋업·실행** → [dev_onboarding.md](dev_onboarding.md)
- **진행·값 가공** → [progress.md](progress.md)
