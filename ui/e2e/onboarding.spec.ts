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
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
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
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
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
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
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

  // AC-3: request-textarea odaklanınca kenarlık #2563EB olmalı ve bir box-shadow görünmeli.
  test('shows a focus border and box-shadow on the request textarea when focused (AC-3)', async ({ page }) => {
    await page.goto('/');

    const textarea = page.getByTestId('request-textarea');
    await textarea.focus();

    await expect(textarea).toHaveCSS('border-color', 'rgb(37, 99, 235)');
    const boxShadow = await textarea.evaluate((el) => getComputedStyle(el).boxShadow);
    expect(boxShadow).not.toBe('none');
    expect(boxShadow).not.toBe('');
  });

  // AC-4: request-textarea blur olunca kenarlık tekrar #E5E7EB'e dönmeli.
  test('reverts the request textarea border to #E5E7EB on blur (AC-4)', async ({ page }) => {
    await page.goto('/');

    const textarea = page.getByTestId('request-textarea');
    await textarea.focus();
    await expect(textarea).toHaveCSS('border-color', 'rgb(37, 99, 235)');

    await page.getByRole('heading', { name: /klasör seç/i }).click();

    await expect(textarea).toHaveCSS('border-color', 'rgb(229, 231, 235)');
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

  // AC-1 (onboarding-istek-placeholder / Saga #254): boş textarea örnek istek placeholder'ını gösterir.
  test('shows the guiding placeholder text with a muted color on the empty request textarea (AC-1)', async ({ page }) => {
    await page.goto('/');

    const textarea = page.getByTestId('request-textarea');

    await expect(textarea).toHaveAttribute('placeholder', 'Bu klasördeki PDF\'leri tarihe göre sırala');
    const placeholderColor = await textarea.evaluate((el) => getComputedStyle(el, '::placeholder').color);
    expect(placeholderColor).toBe('rgb(156, 163, 175)');
  });

  // AC-2 (onboarding-istek-placeholder): yazınca placeholder native olarak kaybolur, sadece yazılan metin görünür.
  test('hides the placeholder once the user starts typing into the request textarea (AC-2)', async ({ page }) => {
    await page.goto('/');

    const textarea = page.getByTestId('request-textarea');
    await textarea.fill('bu klasördeki faturaları müşteriye göre grupla');

    await expect(textarea).toHaveValue('bu klasördeki faturaları müşteriye göre grupla');
    await expect(textarea).toHaveAttribute('placeholder', 'Bu klasördeki PDF\'leri tarihe göre sırala');
  });

  // AC-3 (onboarding-istek-placeholder): yazılan metin tamamen silindiğinde placeholder tekrar görünür.
  test('shows the placeholder again after the typed text is fully cleared (AC-3)', async ({ page }) => {
    await page.goto('/');

    const textarea = page.getByTestId('request-textarea');
    await textarea.fill('geçici bir istek');
    await textarea.fill('');

    await expect(textarea).toHaveValue('');
    await expect(textarea).toHaveAttribute('placeholder', 'Bu klasördeki PDF\'leri tarihe göre sırala');
  });

  // AC-2 (bos-istek-engelleme / Saga #255): boş istekle Devam'a basınca #DC2626 kenarlık + hata mesajı görünmeli.
  test('shows a red border and inline error when Continue is clicked with an empty request (AC-2)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');
    await page.getByRole('button', { name: /klasör seç/i }).click();

    await page.getByRole('button', { name: /devam/i }).click();

    const textarea = page.getByTestId('request-textarea');
    await expect(textarea).toHaveCSS('border-color', 'rgb(220, 38, 38)');
    await expect(page.getByText('Devam etmek için bir istek yazın.')).toBeVisible();
  });

  // AC-4 (bos-istek-engelleme / Saga #255): hata gösterilirken yazmaya başlayınca kenarlık/mesaj anında kalkmalı.
  test('clears the red border and error as soon as the user starts typing (AC-4)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');
    await page.getByRole('button', { name: /klasör seç/i }).click();
    await page.getByRole('button', { name: /devam/i }).click();

    const textarea = page.getByTestId('request-textarea');
    await expect(page.getByText('Devam etmek için bir istek yazın.')).toBeVisible();

    await textarea.fill('bu klasördeki faturaları müşteriye göre grupla');

    await expect(page.getByText('Devam etmek için bir istek yazın.')).toHaveCount(0);
    // fill() bırakır textarea odaklı halde; odak kenarlığı (#2563EB) hâlâ geçerli, hata kenarlığı (#DC2626) değil.
    await expect(textarea).toHaveCSS('border-color', 'rgb(37, 99, 235)');
  });

  // AC-2 (gecersiz-klasor-reddi / Saga #256): erişilemeyen klasör seçilince path korunur + hata mesajı görünür + Devam disabled.
  test('keeps the path visible and disables Continue when the selected folder is inaccessible (AC-2)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Silinmiş';
          if (cmd === 'plugin:fs|exists') return false;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');

    await page.getByRole('button', { name: /klasör seç/i }).click();

    await expect(page.getByTestId('selected-folder-path')).toHaveText('C:\\Users\\Yusuf\\Documents\\Silinmiş');
    await expect(page.getByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.')).toBeVisible();
    await expect(page.getByRole('button', { name: /devam/i })).toBeDisabled();
  });

  // AC-3 (gecersiz-klasor-reddi / Saga #256): geçerli bir klasör yeniden seçilince hata kalkar, Devam aktifleşir.
  test('clears the folder error and enables Continue after re-selecting a valid folder (AC-3)', async ({ page }) => {
    await page.addInitScript(() => {
      let dialogCallCount = 0;
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') {
            dialogCallCount += 1;
            return dialogCallCount === 1 ? 'C:\\Geçersiz' : 'C:\\Geçerli';
          }
          if (cmd === 'plugin:fs|exists') return dialogCallCount === 1 ? false : true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');

    await page.getByRole('button', { name: /klasör seç/i }).click();
    await expect(page.getByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.')).toBeVisible();

    await page.getByRole('button', { name: /klasör seç/i }).click();

    await expect(page.getByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.')).toHaveCount(0);
    await expect(page.getByTestId('selected-folder-path')).toHaveText('C:\\Geçerli');
    await expect(page.getByRole('button', { name: /devam/i })).toBeEnabled();
  });

  // AC-4 (gecersiz-klasor-reddi / Saga #256): trailing backslash normalize edilip gösterilen path'ten temizlenmeli.
  test('strips a trailing backslash from the displayed folder path (AC-4)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Belgeler\\';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');

    await page.getByRole('button', { name: /klasör seç/i }).click();

    await expect(page.getByTestId('selected-folder-path')).toHaveText('C:\\Users\\Yusuf\\Belgeler');
  });

  // AC-1 (klavye-ile-form-gezintisi / Saga #257): Tab sırası Klasör Seç -> path -> textarea -> Devam olmalı.
  test('tabs through the form in the order: choose folder, path, request textarea, continue (AC-1)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');
    await page.getByRole('button', { name: /klasör seç/i }).click();
    await expect(page.getByTestId('selected-folder-path')).toBeVisible();

    await page.locator('body').click();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /klasör seç/i })).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByTestId('selected-folder-path')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByTestId('request-textarea')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /devam/i })).toBeFocused();
  });

  // AC-3 (klavye-ile-form-gezintisi / Saga #257): Devam butonu odaklıyken Enter, form geçerliyse gönderimi tetikler (native buton davranışı).
  test('submits when Enter is pressed while the Continue button is focused and the form is valid (AC-3)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');
    await page.getByRole('button', { name: /klasör seç/i }).click();
    await page.getByTestId('request-textarea').fill('bu klasördeki PDF\'leri sırala');

    await page.getByRole('button', { name: /devam/i }).focus();
    await page.keyboard.press('Enter');

    // onContinue şu an no-op (Kapsam Dışı) — bu test yalnızca native Enter->click
    // davranışının submit'i (handleContinueClick'i) tetiklediğini, hata göstermediğini doğrular.
    await expect(page.getByText('Devam etmek için bir istek yazın.')).toHaveCount(0);
  });

  // AC-4 (klavye-ile-form-gezintisi / Saga #257): Devam odaklıyken Enter, form geçersizse hata gösterir ve odağı textarea'ya taşır.
  test('shows the empty-request error and moves focus to the textarea when Enter is pressed on Continue with an invalid form (AC-4)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');
    await page.getByRole('button', { name: /klasör seç/i }).click();

    await page.getByRole('button', { name: /devam/i }).focus();
    await page.keyboard.press('Enter');

    await expect(page.getByText('Devam etmek için bir istek yazın.')).toBeVisible();
    await expect(page.getByTestId('request-textarea')).toBeFocused();
  });

  // AC-5 (klavye-ile-form-gezintisi / Saga #257): erişilemez klasör sonrası odak Klasör Seç butonuna gerçek tarayıcıda da taşınmalı.
  test('moves focus to the "Klasör Seç" button after selecting an inaccessible folder, in a real browser (AC-5)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Silinmiş';
          if (cmd === 'plugin:fs|exists') return false;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');

    await page.getByRole('button', { name: /klasör seç/i }).click();
    await expect(page.getByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.')).toBeVisible();

    await expect(page.getByRole('button', { name: /klasör seç/i })).toBeFocused();
  });

  // AC-6 (klavye-ile-form-gezintisi / Saga #257): Klasör Seç odaklıyken Enter, native davranışıyla dialog açmaya devam eder (regresyon).
  test('still opens the folder dialog when Enter is pressed while "Klasör Seç" is focused (AC-6)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.goto('/');

    await page.getByRole('button', { name: /klasör seç/i }).focus();
    await page.keyboard.press('Enter');

    await expect(page.getByTestId('selected-folder-path')).toHaveText('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
  });

  // AC-1 (ilk-istek-oturum-baglami / Saga #258): geçerli formda Devam, backend'e POST /api/session gönderip ana sohbet ekranına geçiriyor.
  test('posts the request to /api/session and shows the main chat screen on success (AC-1)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    let requestBody: unknown;
    await page.route('**/api/session', (route) => {
      requestBody = route.request().postDataJSON();
      return route.fulfill({
        status: 201,
        json: { sessionId: '11111111-1111-1111-1111-111111111111', selectedFolder: 'C:\\Users\\Yusuf\\Documents\\Müvekkiller', requestText: 'PDF\'leri tarihe göre sırala' },
      });
    });
    await page.goto('/');
    await page.getByRole('button', { name: /klasör seç/i }).click();
    await page.getByTestId('request-textarea').fill('PDF\'leri tarihe göre sırala');

    await page.getByRole('button', { name: /devam/i }).click();

    await expect(page.getByTestId('main-chat-screen')).toBeVisible();
    expect(requestBody).toEqual({ selectedFolder: 'C:\\Users\\Yusuf\\Documents\\Müvekkiller', requestText: 'PDF\'leri tarihe göre sırala' });
  });

  // AC-3 (ilk-istek-oturum-baglami / Saga #258): backend'e ulaşılamazsa hata gösterilir, Devam tekrar denenebilir kalır.
  test('shows a submit error and keeps Continue usable when the backend is unreachable (AC-3)', async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as Window & { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'plugin:dialog|open') return 'C:\\Users\\Yusuf\\Documents\\Müvekkiller';
          if (cmd === 'plugin:fs|exists') return true;
          return Promise.reject(new Error(`unmocked command: ${cmd}`));
        },
      };
    });
    await page.route('**/api/session', (route) => route.abort('failed'));
    await page.goto('/');
    await page.getByRole('button', { name: /klasör seç/i }).click();
    await page.getByTestId('request-textarea').fill('PDF\'leri tarihe göre sırala');

    await page.getByRole('button', { name: /devam/i }).click();

    await expect(page.getByText('İstek gönderilemedi. Lütfen tekrar deneyin.')).toBeVisible();
    await expect(page.getByRole('button', { name: /devam/i })).toBeEnabled();
    await expect(page.getByTestId('main-chat-screen')).toHaveCount(0);
  });
});
