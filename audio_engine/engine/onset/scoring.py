"""
L4 Aggregation: 레이어 스코어·할당 (지표 딕셔너리 → P0/P1/P2).
L1, L3 결과(딕셔너리)만 사용.
트랙별 1차 정규화(adaptive)로 곡마다 분포에 맞춰 상대적 비교 가능.
"""
from __future__ import annotations

import numpy as np

# P0 (저정밀/메인 타격): E↑ T↑ C↑ - D + F
W_E_P0 = 0.20
W_T_P0 = 0.40
W_C_P0 = 0.40
W_D_P0 = 0.10
W_F_P0 = 0.08

# P1 (중정밀): T↑ + mid(E) + C
W_T_P1 = 0.25
W_E_P1 = 0.25
W_C_P1 = 0.30

# P2 (고정밀): D↑ + (1-F) + (1-C) + (1-E)
W_D_P2 = 0.35
W_F_P2 = 0.25
W_C_P2 = 0.20
W_E_P2 = 0.20


def normalize_metrics_per_track(
    metrics: dict[str, np.ndarray],
    use_percentile: bool = True,
    low: float = 1.0,
    high: float = 99.0,
) -> dict[str, np.ndarray]:
    """
    1차 분석: 트랙 내 지표 분포로 각 메트릭을 0~1로 재정규화.
    곡마다 절대값 스케일이 달라도, 같은 가중치로 "상대적으로 뚜렷한 타격 → P0"이 되도록 함.
    use_percentile=True면 low~high 백분위로 클리핑 후 min-max. False면 전체 min-max.
    """
    out = {}
    for key, arr in metrics.items():
        valid = np.isfinite(arr)
        if np.sum(valid) < 2:
            out[key] = np.clip(np.nan_to_num(arr, nan=0.5), 0, 1)
            continue
        if use_percentile:
            p_lo = np.nanpercentile(arr, low)
            p_hi = np.nanpercentile(arr, high)
            if p_hi <= p_lo:
                out[key] = np.clip(np.nan_to_num(arr, nan=0.5), 0, 1)
                continue
            x = (arr - p_lo) / (p_hi - p_lo)
        else:
            a, b = np.nanmin(arr), np.nanmax(arr)
            if b <= a:
                out[key] = np.clip(np.nan_to_num(arr, nan=0.5), 0, 1)
                continue
            x = (arr - a) / (b - a)
        out[key] = np.clip(np.nan_to_num(x, nan=0.5), 0, 1)
    return out


def _mid_energy(E: np.ndarray) -> np.ndarray:
    """E가 중간(0.3~0.7)일 때 높은 값. 1 - 4*(E-0.5)^2 (0~1 클리핑)."""
    x = 1.0 - 4.0 * (E - 0.5) ** 2
    return np.clip(x, 0, 1)


def compute_layer_scores(
    metrics: dict[str, np.ndarray],
    *,
    adaptive: bool = True,
    use_percentile: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    metrics: {"energy": E, "clarity": C, "temporal": T, "focus": F, "dependency": D}
    각 0~1 배열, 길이 동일.
    adaptive=True면 먼저 트랙 내 분포로 지표를 0~1 재정규화한 뒤 가중치 적용 (곡별 상대 비교).
    반환: (S0, S1, S2) 각 P0/P1/P2 스코어 배열.
    """
    if adaptive:
        metrics = normalize_metrics_per_track(metrics, use_percentile=use_percentile)
    E = metrics["energy"]
    C = metrics["clarity"]
    T = metrics["temporal"]
    F = metrics["focus"]
    D = metrics["dependency"]

    S0 = (
        W_E_P0 * E
        + W_T_P0 * T
        + W_C_P0 * C
        - W_D_P0 * D
        + W_F_P0 * F
    )
    S1 = W_T_P1 * T + W_E_P1 * _mid_energy(E) + W_C_P1 * C
    S2 = (
        W_D_P2 * D
        + W_F_P2 * (1.0 - F)
        + W_C_P2 * (1.0 - C)
        + W_E_P2 * (1.0 - E)
    )
    S0 = np.clip(S0, 0, 1)
    S1 = np.clip(S1, 0, 1)
    S2 = np.clip(S2, 0, 1)
    return S0, S1, S2


def assign_layer(
    S0: np.ndarray,
    S1: np.ndarray,
    S2: np.ndarray,
) -> np.ndarray:
    """
    layer_indices: 0=P0, 1=P1, 2=P2. argmax(S0, S1, S2) per event.
    """
    stacked = np.stack([S0, S1, S2], axis=1)
    return np.argmax(stacked, axis=1)


def apply_layer_floor(
    layer_indices: np.ndarray,
    S0: np.ndarray,
    S1: np.ndarray,
    S2: np.ndarray,
    *,
    min_p0_ratio: float = 0.20,
    min_p0_p1_ratio: float = 0.40,
) -> np.ndarray:
    """
    레이어 비율 하한 보정: P0 >= min_p0_ratio, P0+P1 >= min_p0_p1_ratio.
    부족하면 S0/S1 순으로 P2→P1→P0으로 승격.
    """
    layers = np.asarray(layer_indices).copy()
    n = len(layers)
    if n == 0:
        return layers

    target_p0 = max(1, int(np.ceil(n * min_p0_ratio)))
    target_p0_p1 = max(1, int(np.ceil(n * min_p0_p1_ratio)))

    n_p0 = np.sum(layers == 0)
    n_p1 = np.sum(layers == 1)
    n_p2 = np.sum(layers == 2)

    # 1) P0 부족: P1·P2 중 S0가 높은 순으로 P0으로 승격
    if n_p0 < target_p0:
        need = target_p0 - n_p0
        non_p0 = np.where(layers != 0)[0]
        # S0 기준 내림차순 → 상위 need개 인덱스
        order = non_p0[np.argsort(-S0[non_p0])]
        promote_to_p0 = order[:need]
        layers[promote_to_p0] = 0
        n_p0 = np.sum(layers == 0)
        n_p1 = np.sum(layers == 1)
        n_p2 = np.sum(layers == 2)

    # 2) P0+P1 부족: P2 중 S1이 높은 순으로 P1으로 승격
    if (n_p0 + n_p1) < target_p0_p1:
        need = target_p0_p1 - (n_p0 + n_p1)
        p2_idx = np.where(layers == 2)[0]
        if len(p2_idx) > 0:
            order = p2_idx[np.argsort(-S1[p2_idx])]
            promote_to_p1 = order[: min(need, len(order))]
            layers[promote_to_p1] = 1

    return layers
