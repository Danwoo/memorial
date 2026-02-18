import { test, expect } from '@playwright/test'

test.describe('채팅 (데모 모드)', () => {
  test('데모 모드 → 채팅 화면 렌더링', async ({ page }) => {
    await page.goto('/demo/chat')
    await expect(page.locator('.chat-view, .chat-container')).toBeVisible({ timeout: 10_000 })
  })

  test('데모 모드 → 채팅 메시지 표시', async ({ page }) => {
    await page.goto('/demo/chat')
    await expect(page.locator('.chat-message, .message-bubble')).toBeVisible({ timeout: 10_000 })
  })

  test('데모 모드 → 수정 시도 시 토스트 안내', async ({ page }) => {
    await page.goto('/demo/chat')
    const input = page.locator('textarea, .chat-input, input[type="text"]').first()
    if (await input.isVisible()) {
      await input.fill('테스트 메시지')
      await page.keyboard.press('Enter')
      await expect(page.locator('.toast')).toBeVisible({ timeout: 5_000 })
    }
  })
})
