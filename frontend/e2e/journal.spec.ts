import { test, expect } from '@playwright/test'

test.describe('저널 (데모 모드)', () => {
  test('데모 모드 → 저널 화면 렌더링', async ({ page }) => {
    await page.goto('/demo/journal')
    await expect(page.locator('.journal-view, .journal-container')).toBeVisible({ timeout: 10_000 })
  })

  test('데모 모드 → 저널 날짜 목록 표시', async ({ page }) => {
    await page.goto('/demo/journal')
    await expect(page.locator('.journal-date-item, .date-list-item')).toBeVisible({ timeout: 10_000 })
  })
})
