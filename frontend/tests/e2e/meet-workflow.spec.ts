import { test, expect } from '@playwright/test';

// Set viewport to ensure desktop view (mode buttons hidden on mobile)
test.use({ viewport: { width: 1280, height: 720 } });

test.describe('AquaForge Navigation', () => {
  
  test('should display home page with navigation', async ({ page }) => {
    await page.goto('/');
    // Check header brand
    await expect(page.locator('text=AquaForge')).toBeVisible();
  });

  test('should navigate to meet setup page', async ({ page }) => {
    await page.goto('/');
    // Use more specific selector
    await page.locator('a[href="/meet"]').first().click();
    await expect(page).toHaveURL('/meet');
    await expect(page.getByRole('heading', { name: /Meet Setup/i })).toBeVisible();
  });

  test('should navigate to optimize page', async ({ page }) => {
    await page.goto('/optimize');
    await expect(page.getByRole('heading', { name: 'Optimizer', exact: true })).toBeVisible();
  });

  test('should navigate to results page', async ({ page }) => {
    await page.goto('/results');
    await expect(page.getByRole('heading', { name: 'Results', exact: true })).toBeVisible();
  });

});

test.describe('Mode Switching', () => {

  test('should show mode switcher in header', async ({ page }) => {
    await page.goto('/');
    // Use data-testid selectors
    await expect(page.locator('[data-testid="mode-dual"]')).toBeVisible();
    await expect(page.locator('[data-testid="mode-championship"]')).toBeVisible();
  });

  test('should switch to championship mode', async ({ page }) => {
    await page.goto('/meet');
    
    // Click championship mode
    await page.locator('[data-testid="mode-championship"]').click();
    
    // Verify badge changes (case-insensitive)
    await expect(page.locator('.badge').filter({ hasText: /championship/i })).toBeVisible();
  });

  test('should switch back to dual mode', async ({ page }) => {
    await page.goto('/meet');
    
    // Switch to championship first
    await page.locator('[data-testid="mode-championship"]').click();
    await page.waitForTimeout(300);
    
    // Switch back to dual
    await page.locator('[data-testid="mode-dual"]').click();
    
    // Verify
    await expect(page.locator('.badge').filter({ hasText: /dual/i })).toBeVisible();
  });

});

test.describe('Optimize Page', () => {

  test('dual mode should show VISAA scoring options', async ({ page }) => {
    await page.goto('/optimize');
    await expect(page.getByText(/VISAA/i)).toBeVisible();
  });

  test('championship mode should show VCAC scoring option', async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-testid="mode-championship"]').click();
    await page.goto('/optimize');
    await expect(page.getByText(/VCAC/i)).toBeVisible();
  });

});

test.describe('Meet Setup Page', () => {

  test('should have tab navigation', async ({ page }) => {
    await page.goto('/meet');
    
    // Check tabs exist (case insensitive)
    await expect(page.locator('button').filter({ hasText: /setup/i })).toBeVisible();
    await expect(page.locator('button').filter({ hasText: /upload/i })).toBeVisible();
    await expect(page.locator('button').filter({ hasText: /roster/i })).toBeVisible();
  });

  test('should switch to roster tab', async ({ page }) => {
    await page.goto('/meet');
    
    // Click roster tab
    await page.locator('button').filter({ hasText: /roster/i }).click();
    
    // Should show empty state
    await expect(page.getByText('Upload Seton team data to view roster')).toBeVisible();
  });

  test('should show meet selector', async ({ page }) => {
    await page.goto('/meet');
    await expect(page.getByText(/Select Meet/i)).toBeVisible();
  });

});
