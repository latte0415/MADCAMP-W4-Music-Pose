"""
09. Layered Export (레이어별 JSON 추출)
5개 피처 계산 → P0/P1/P2 스코어·할당 → 레이어별 통합 JSON 저장.
엔트리: engine.onset 사용.
"""
import sys
import os


def find_project_root():
    cwd = os.path.abspath(os.getcwd())
    while cwd:
        if os.path.isdir(os.path.join(cwd, "audio_engine")) and os.path.isdir(
            os.path.join(cwd, "web")
        ):
            return cwd
        cwd = os.path.dirname(cwd)
    return os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), "..", ".."))


project_root = find_project_root()
sys.path.insert(0, project_root)

from audio_engine.engine.onset import (
    build_context,
    compute_energy,
    compute_clarity,
    compute_temporal,
    compute_spectral,
    compute_context_dependency,
    compute_layer_scores,
    assign_layer,
    apply_layer_floor,
    write_layered_json,
)

# %%
# 기본 입력: 샘플 오디오 (필요 시 경로 변경)
audio_path = os.path.join(
    project_root,
    "audio_engine",
    "samples",
    "stems",
    "htdemucs",
    "sample_ropes_short",
    "drums.wav",
)
# audio_path = os.path.join(project_root, "audio_engine", "samples", "sample_ropes_short.mp3")

ctx = build_context(audio_path, include_temporal=True)
print(f"파일: {os.path.basename(audio_path)}")
print(f"샘플링 레이트: {ctx.sr} Hz, 길이: {ctx.duration:.2f} 초")
print(f"검출된 타격점 수: {ctx.n_events}")
print(f"BPM: {ctx.bpm:.1f}")

# %%
e_s, _ = compute_energy(ctx)
c_s, _ = compute_clarity(ctx)
t_s, _ = compute_temporal(ctx)
f_s, _ = compute_spectral(ctx)
d_s, _ = compute_context_dependency(ctx)

metrics = {
    "energy": e_s,
    "clarity": c_s,
    "temporal": t_s,
    "focus": f_s,
    "dependency": d_s,
}
S0, S1, S2 = compute_layer_scores(metrics)
layer_indices = assign_layer(S0, S1, S2)
# P0 >= 20%, P0+P1 >= 40% 보정
layer_indices = apply_layer_floor(
    layer_indices, S0, S1, S2,
    min_p0_ratio=0.20,
    min_p0_p1_ratio=0.40,
)
for i, name in enumerate(["P0", "P1", "P2"]):
    n = (layer_indices == i).sum()
    print(f"  {name}: {n}개")

# %%
samples_dir = os.path.join(project_root, "audio_engine", "samples")
json_path = os.path.join(samples_dir, "onset_events_layered.json")
write_layered_json(
    ctx,
    metrics,
    layer_indices,
    json_path,
    source=os.path.basename(audio_path),
    project_root=project_root,
)
print(f"저장 완료: {json_path}")
