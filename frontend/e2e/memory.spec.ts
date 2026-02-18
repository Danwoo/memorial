import { test, expect } from '@playwright/test'

// 메모리 테스트는 인증 필요 — 데모 모드 도입 후 데모 데이터로 테스트
test.describe('메모리 CRUD (데모 모드)', () => {
  test('데모 모드 → 메모리 목록 표시', async ({ page }) => {
    await page.goto('/demo/memories')
    await expect(page.locator('.memory-card, .memory-grid')).toBeVisible({ timeout: 10_000 })
  })

  test('데모 모드 → 메모리 카드 클릭 → 상세 모달', async ({ page }) => {
    await page.goto('/demo/memories')
    await page.waitForSelector('.memory-card', { timeout: 10_000 })
    await page.click('.memory-card >> nth=0')
    await expect(page.locator('.memory-detail-modal, .modal-overlay')).toBeVisible({ timeout: 5_000 })
  })

  test('데모 모드 → 필터바 렌더링', async ({ page }) => {
    await page.goto('/demo/memories')
    await expect(page.locator('.filter-bar')).toBeVisible({ timeout: 10_000 })
  })
})
