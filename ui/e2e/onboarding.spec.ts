import { expect, test } from '@playwright/test';

test.describe('first-run folder onboarding', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/health', (route) => route.fulfill({ json: { status: 'ok' } }));
    await page.route('**/api/config', (route) => route.fulfill({ status: 404 }));
  });

  test('shows an enabled folder chooser within 500ms on a first run with a ready backend', async ({ page }) => {
    // Warm-up navigation so Vite's cold-compile time isn't counted in the measured render time.
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /klasör seç/i })).toBeVisible();

    const loadedAt = Date.now();
    await page.reload();

    await expect(page.getByRole('heading', { name: /klasör seç/i })).toBeVisible({ timeout: 500 });
    expect(Date.now() - loadedAt).toBeLessThan(500);
    await expect(page.getByRole('button', { name: /klasör seç/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /devam/i })).toBeDisabled();
  });

  test('shows the chosen native-dialog folder and enables Continue', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) =>
          cmd === 'plugin:dialog|open' ? 'C:\\Users\\Yusuf\\Documents\\Müvekkiller' : Promise.reject(new Error(`unmocked command: ${cmd}`)),
      };
    });
    await page.goto('/');

    await page.getByRole('button', { name: /klasör seç/i }).click();

    await expect(page.getByTestId('selected-folder-path')).toHaveText('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
    await expect(page.getByRole('button', { name: /devam/i })).toBeEnabled();
  });

  test('leaves Continue disabled when the native dialog is cancelled', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => (cmd === 'plugin:dialog|open' ? null : Promise.reject(new Error(`unmocked command: ${cmd}`))),
      };
    });
    await page.goto('/');

    await page.getByRole('button', { name: /klasör seç/i }).click();

    await expect(page.getByTestId('selected-folder-path')).toHaveCount(0);
    await expect(page.getByRole('button', { name: /devam/i })).toBeDisabled();
  });

  test('disables onboarding while the backend is starting, then shows retry after ten seconds', async ({ page }) => {
    await page.route('**/api/health', (route) => route.abort('failed'));
    await page.goto('/');

    await expect(page.getByText(/başlatılıyor/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /klasör seç/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /devam/i })).toBeDisabled();
    await expect(page.getByText(/backend.*(ulaşılamadı|zaman aşımı)/i)).toBeVisible({ timeout: 10_500 });
    await expect(page.getByRole('button', { name: /tekrar dene/i })).toBeVisible();
  });

  test('skips onboarding entirely when a saved config already exists', async ({ page }) => {
    await page.route('**/api/config', (route) => route.fulfill({ json: { selectedFolder: 'C:\\Users\\Yusuf\\Documents' } }));
    await page.goto('/');

    await expect(page.getByRole('heading', { name: /klasör seç/i })).toHaveCount(0);
    await expect(page.getByTestId('main-chat-screen')).toBeVisible();
  });

  // AC-2: klavye ile Tab yapılınca görünür bir odak halkası (outline) olmalı.
  test('shows a visible focus ring on the "Klasör Seç" button when tabbed to (AC-2)', async ({ page }) => {
    await page.goto('/');

    const button = page.getByRole('button', { name: /klasör seç/i });
    await expect(button).toBeEnabled();

    await page.keyboard.press('Tab');

    await expect(button).toBeFocused();

    const outline = await button.evaluate((el) => {
      const style = getComputedStyle(el);
      return { style: style.outlineStyle, width: style.outlineWidth, color: style.outlineColor };
    });

    expect(outline.style).not.toBe('none');
    expect(outline.width).toBe('2px');
    expect(outline.color).not.toBe('transparent');
  });

  // AC-2: klavye ile Tab yapıp odak selected-folder-path'e gelince tam yolu içeren tooltip görünmeli.
  test('shows a full-path tooltip when tabbing focus to the selected folder path (AC-2)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) =>
          cmd === 'plugin:dialog|open' ? 'C:\\Users\\Yusuf\\Documents\\Müvekkiller' : Promise.reject(new Error(`unmocked command: ${cmd}`)),
      };
    });
    await page.goto('/');

    await page.getByRole('button', { name: /klasör seç/i }).click();

    const pathElement = page.getByTestId('selected-folder-path');
    await expect(pathElement).toBeVisible();
    await pathElement.focus();

    await expect(page.getByTestId('folder-path-tooltip')).toBeVisible();
    await expect(page.getByTestId('folder-path-tooltip')).toHaveText('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
  });

  // AC-3: fare ile hover yapılınca aynı tooltip mekanizması tam yolu göstermeli.
  test('shows the same full-path tooltip on mouse hover over the selected folder path (AC-3)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) =>
          cmd === 'plugin:dialog|open' ? 'C:\\Users\\Yusuf\\Documents\\Müvekkiller' : Promise.reject(new Error(`unmocked command: ${cmd}`)),
      };
    });
    await page.goto('/');

    await page.getByRole('button', { name: /klasör seç/i }).click();

    const pathElement = page.getByTestId('selected-folder-path');
    await expect(pathElement).toBeVisible();
    await pathElement.hover();

    await expect(page.getByTestId('folder-path-tooltip')).toBeVisible();
    await expect(page.getByTestId('folder-path-tooltip')).toHaveText('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
  });

  // AC-4: hover ve active durumlarında buton arka planı koyulaşmalı.
  test('darkens the "Klasör Seç" button background on hover and active (AC-4)', async ({ page }) => {
    await page.goto('/');

    const button = page.getByRole('button', { name: /klasör seç/i });

    await button.hover();
    await expect(button).toHaveCSS('background-color', 'rgb(29, 78, 216)');

    await page.mouse.down();
    await expect(button).toHaveCSS('background-color', 'rgb(30, 64, 175)');
    await page.mouse.up();
  });
});
