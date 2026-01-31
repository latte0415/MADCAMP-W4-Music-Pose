/**
 * 분석 이벤트 — 시각화용 JSON 형식
 * t: 시간(초), strength: 점 크기(0~1), texture: 세로 위치(height, 0~1), color: hex, layer: 레이어명
 */
export interface EventPoint {
  t: number;
  strength: number;
  texture?: number;
  color: string;
  layer: string;
}
