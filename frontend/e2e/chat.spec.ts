import { test, expect } from '@playwright/test'

test.describe('소크라테스 (데모 모드)', () => {
  test('데모 모드 → 다이어리 우측 패널에서 Socrates 탭 렌더링', async ({ page }) => {
    await page.goto('/demo/diary')
    await expect(page.locator('.diary-right-panel__tab').filter({ hasText: 'Socrates' })).toBeVisible({ timeout: 10_000 })
  })

  test('데모 모드 → Socrates 탭 클릭 → 채팅 패널 표시', async ({ page }) => {
    await page.goto('/demo/diary')
    const socratesTab = page.locator('.diary-right-panel__tab').filter({ hasText: 'Socrates' })
    await socratesTab.click({ timeout: 10_000 })
    await expect(page.locator('.socrates-panel')).toBeVisible({ timeout: 5_000 })
  })

  test('데모 모드 → Socrates 패널 입력창 렌더링', async ({ page }) => {
    await page.goto('/demo/diary')
    const socratesTab = page.locator('.diary-right-panel__tab').filter({ hasText: 'Socrates' })
    await socratesTab.click({ timeout: 10_000 })
    await expect(page.locator('.socrates-panel')).toBeVisible({ timeout: 5_000 })
    await expect(page.locator('.socrates-input')).toBeVisible({ timeout: 5_000 })
  })
})
