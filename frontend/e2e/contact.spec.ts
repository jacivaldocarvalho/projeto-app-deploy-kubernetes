import { test, expect } from '@playwright/test'

test('submits the real form and displays success', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'A conversation starts here.' })).toBeVisible()
  await page.getByLabel('Your name').fill('Browser validation')
  await page.getByLabel('Email address').fill('browser@example.com')
  await page.getByLabel('Your message').fill(`browser-${Date.now()}`)
  await page.getByRole('button', { name: 'Send message' }).click()
  await expect(page.getByRole('status')).toContainText('Message saved successfully')
  await expect(page.getByLabel('Your message')).toHaveValue('')
})

test('native validation prevents an invalid email request', async ({ page }) => {
  let submissions = 0
  page.on('request', request => { if (request.method() === 'POST') submissions++ })
  await page.goto('/index.php')
  await page.getByLabel('Your name').fill('Browser validation')
  await page.getByLabel('Email address').fill('invalid')
  await page.getByLabel('Your message').fill('Hello')
  await page.getByRole('button', { name: 'Send message' }).click()
  expect(await page.getByLabel('Email address').evaluate((input: HTMLInputElement) => input.validity.valid)).toBe(false)
  expect(submissions).toBe(0)
})

test('preserves input when the backend is unavailable', async ({ page }) => {
  await page.goto('/')
  await page.route('**/index.php', route => route.fulfill({ status: 503, body: 'Internal details' }))
  await page.getByLabel('Your name').fill('Browser validation')
  await page.getByLabel('Email address').fill('browser@example.com')
  await page.getByLabel('Your message').fill('Please keep this message')
  await page.getByRole('button', { name: 'Send message' }).click()
  await expect(page.getByRole('alert')).toContainText('Unable to save the message')
  await expect(page.getByLabel('Your message')).toHaveValue('Please keep this message')
})

test('fits a mobile viewport and supports keyboard focus', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await page.goto('/')
  await expect(page.getByLabel('Your name')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.getByLabel('Your name').focus()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('Email address')).toBeFocused()
})
