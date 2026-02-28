import { test, expect } from '@playwright/test'

test.describe('스크랩 CRUD (데모 모드)', () => {
  test('데모 모드 → 스크랩 목록 표시', async ({ page }) => {
    await page.goto('/demo/scraps')
    await expect(page.locator('.scrap-list')).toBeVisible({ timeout: 10_000 })
  })

  test('데모 모드 → 스크랩 행 클릭 → 상세 모달', async ({ page }) => {
    await page.goto('/demo/scraps')
    await page.waitForSelector('.scrap-list-row', { timeout: 10_000 })
    await page.click('.scrap-list-row >> nth=0')
    await expect(page.locator('.scrap-detail-modal')).toBeVisible({ timeout: 5_000 })
  })

  test('데모 모드 → 필터바 렌더링', async ({ page }) => {
    await page.goto('/demo/scraps')
    await expect(page.locator('.filter-bar')).toBeVisible({ timeout: 10_000 })
  })
})
