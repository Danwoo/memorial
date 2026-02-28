import { test, expect } from '@playwright/test'

test.describe('다이어리 (데모 모드)', () => {
  test('데모 모드 → 다이어리 화면 렌더링', async ({ page }) => {
    await page.goto('/demo/diary')
    await expect(page.locator('.diary-view')).toBeVisible({ timeout: 10_000 })
  })

  test('데모 모드 → 다이어리 날짜 네비게이션 표시', async ({ page }) => {
    await page.goto('/demo/diary')
    await expect(page.locator('.diary-date-nav')).toBeVisible({ timeout: 10_000 })
  })
})
