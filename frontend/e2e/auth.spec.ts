import { test, expect } from '@playwright/test'

test.describe('인증 플로우', () => {
  test('랜딩 페이지 → 로그인 페이지 이동', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.landing-hero')).toBeVisible()
    await page.click('.landing-cta')
    await expect(page).toHaveURL(/\/login/)
  })

  test('비인증 → 보호 라우트 접근 시 리다이렉트', async ({ page }) => {
    await page.goto('/chat')
    await expect(page).toHaveURL(/\/login/)
  })

  test('비인증 → /memories 접근 시 리다이렉트', async ({ page }) => {
    await page.goto('/memories')
    await expect(page).toHaveURL(/\/login/)
  })

  test('랜딩 페이지 핵심 요소 렌더링', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.landing-headline')).toContainText('기억')
    await expect(page.locator('.landing-feature-grid')).toBeVisible()
    await expect(page.locator('.landing-tech-list')).toBeVisible()
  })
})
