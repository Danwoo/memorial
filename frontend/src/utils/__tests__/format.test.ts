import { describe, it, expect } from 'vitest'
import { getSimilarityLevel } from '../format'

describe('getSimilarityLevel', () => {
  it('0.8 이상이면 "high" 반환', () => {
    expect(getSimilarityLevel(0.8)).toBe('high')
    expect(getSimilarityLevel(0.85)).toBe('high')
    expect(getSimilarityLevel(1.0)).toBe('high')
    expect(getSimilarityLevel(0.95)).toBe('high')
  })

  it('0.5 이상 0.8 미만이면 "medium" 반환', () => {
    expect(getSimilarityLevel(0.5)).toBe('medium')
    expect(getSimilarityLevel(0.7)).toBe('medium')
    expect(getSimilarityLevel(0.79)).toBe('medium')
    expect(getSimilarityLevel(0.65)).toBe('medium')
  })

  it('0.5 미만이면 "low" 반환', () => {
    expect(getSimilarityLevel(0)).toBe('low')
    expect(getSimilarityLevel(0.1)).toBe('low')
    expect(getSimilarityLevel(0.49)).toBe('low')
    expect(getSimilarityLevel(0.3)).toBe('low')
  })

  it('경계값 정확히 처리', () => {
    // 정확히 0.8 → high
    expect(getSimilarityLevel(0.8)).toBe('high')
    // 정확히 0.5 → medium
    expect(getSimilarityLevel(0.5)).toBe('medium')
    // 0.8 바로 아래 → medium
    expect(getSimilarityLevel(0.7999)).toBe('medium')
    // 0.5 바로 아래 → low
    expect(getSimilarityLevel(0.4999)).toBe('low')
  })
})
