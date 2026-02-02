# 레이어링 설계 (실제 코드 반영)

이벤트 단위 5개 지표, P0/P1/P2 방향, **실제 스코어 공식·가중치**를 정리합니다.

---

## 0. 전제: 단위는 "이벤트(타격)"

Onset detection으로 타격 이벤트(시간 `t_i`)를 잡고, 각 이벤트마다 지표를 계산·점수화합니다.

---

## 1. 5개 지표 (구현 기준)

| 지표 | 모듈 | 출력 | 의미 |
|------|------|------|------|
| Energy | `features/energy.py` | `energy_score` 0~1 | RMS·대역 에너지, robust_norm(log_rms). 온셋 간 구간 [mid_prev, mid_next] |
| Clarity | `features/clarity.py` | `clarity_score` 0~1 | Attack time(10%→90%), peak_salience × (1/attack_time). 가변 윈도우 |
| Temporal | `features/temporal.py` | `temporal_score` 0~1 | grid_align × repetition, 가변 그리드·로컬 템포 |
| Focus | `features/spectral.py` | `focus_score` 0~1 | 1 - 0.5×norm(flatness) - 0.5×norm(bandwidth). centroid/bandwidth/flatness |
| Dependency | `features/context.py` | `dependency_score` 0~1 | 1 - norm(SNR). Local SNR·대역별 마스킹 |

---

## 2. 레이어 스코어 공식 (scoring.py)

**정규화**: `compute_layer_scores(metrics, adaptive=True)` 시 `normalize_metrics_per_track()`로 트랙 내 1~99 백분위 재정규화 후 가중치 적용.

**P0 (저정밀/메인 타격)**  
`S0 = W_E_P0*E + W_T_P0*T + W_C_P0*C - W_D_P0*D + W_F_P0*F` → clip 0~1

- W_E_P0=0.20, W_T_P0=0.40, W_C_P0=0.40, W_D_P0=0.10, W_F_P0=0.08

**P1 (중정밀)**  
`S1 = W_T_P1*T + W_E_P1*_mid_energy(E) + W_C_P1*C` → clip 0~1

- W_T_P1=0.25, W_E_P1=0.25, W_C_P1=0.30  
- `_mid_energy(E) = 1 - 4*(E-0.5)^2` (0~1 클리핑). E가 중간일 때 높음.

**P2 (고정밀)**  
`S2 = W_D_P2*D + W_F_P2*(1-F) + W_C_P2*(1-C) + W_E_P2*(1-E)` → clip 0~1

- W_D_P2=0.35, W_F_P2=0.25, W_C_P2=0.20, W_E_P2=0.20

**할당**: `assign_layer(S0, S1, S2)` → `layer_indices = argmax(S0, S1, S2)` (0=P0, 1=P1, 2=P2).

---

## 3. 레이어 비율 보정 (apply_layer_floor)

`apply_layer_floor(layer_indices, S0, S1, S2, min_p0_ratio=0.20, min_p0_p1_ratio=0.40)`:

- P0 비율 < 20% → P1·P2 중 S0가 높은 순으로 P0 승격.
- P0+P1 비율 < 40% → P2 중 S1이 높은 순으로 P1 승격.

---

## 4. 방향성 요약

| 레이어 | 조건 | 의미 |
|--------|------|------|
| **P0** | Energy↑ + Temporal↑ + Clarity↑ − Dependency + Focus | 누구나 듣는 핵심 타격 |
| **P1** | Temporal↑ + Energy 중간 + Clarity↑ | 패턴 유지에 필요 |
| **P2** | Dependency↑ + (1−Focus) + (1−Clarity) + (1−Energy) | 뉘앙스·고정밀 |
