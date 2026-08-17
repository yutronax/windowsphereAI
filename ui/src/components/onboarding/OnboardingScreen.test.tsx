import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { open } from '@tauri-apps/plugin-dialog';
import { invoke } from '@tauri-apps/api/core';

import OnboardingScreen from './OnboardingScreen';

vi.mock('@tauri-apps/plugin-dialog', () => ({
  open: vi.fn(),
}));

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
}));

const openFolderDialog = vi.mocked(open);
const invokeTauriCommand = vi.mocked(invoke);

// Dosya geneli varsayılan: /api/session çağrısı başarılı döner, aksini
// belirten testler (ilk-istek-oturum-baglami describe bloğu) kendi
// beforeEach'inde farklı bir davranış stub'lar.
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ sessionId: 'test-session-id', selectedFolder: '', requestText: '' }),
  }));
});

describe('OnboardingScreen', () => {
  beforeEach(() => {
    openFolderDialog.mockReset();
    invokeTauriCommand.mockReset();
    invokeTauriCommand.mockResolvedValue(true);
  });

  it('renders the first-run folder chooser within 500ms when the backend is ready', () => {
    const startedAt = performance.now();

    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    expect(performance.now() - startedAt).toBeLessThan(500);
    expect(screen.getByRole('heading', { name: /klasör seç/i })).toBeVisible();
    expect(screen.getByRole('button', { name: /klasör seç/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /devam/i })).toBeDisabled();
  });

  it('shows the folder selected in the native dialog and enables Continue', async () => {
    openFolderDialog.mockResolvedValue('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    expect(openFolderDialog).toHaveBeenCalledWith({ directory: true, multiple: false });
    expect(await screen.findByText('C:\\Users\\Yusuf\\Documents\\Müvekkiller')).toBeVisible();
    expect(screen.getByRole('button', { name: /devam/i })).toBeEnabled();
  });

  it('keeps the selection empty and Continue disabled when the native dialog is cancelled', async () => {
    openFolderDialog.mockResolvedValue(null);
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    await waitFor(() => expect(openFolderDialog).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('button', { name: /devam/i })).toBeDisabled();
    expect(screen.queryByTestId('selected-folder-path')).not.toBeInTheDocument();
  });

  it('disables all onboarding interactions while the backend is starting', () => {
    render(<OnboardingScreen backendStatus="starting" onContinue={vi.fn()} />);

    expect(screen.getByText(/başlatılıyor/i)).toBeVisible();
    expect(screen.getByRole('button', { name: /klasör seç/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /devam/i })).toBeDisabled();
  });

  it('shows a timeout error and offers retry when the backend health check expires', () => {
    const onRetry = vi.fn();
    render(<OnboardingScreen backendStatus="backend_timeout" onContinue={vi.fn()} onRetry={onRetry} />);

    expect(screen.getByText(/backend.*(ulaşılamadı|zaman aşımı)/i)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: /tekrar dene/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  // AC-1: enabled "Klasör Seç" butonu birincil eylem stiline sahip olmalı.
  it('renders the enabled "Klasör Seç" button with primary-action styling (AC-1)', () => {
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    const button = screen.getByRole('button', { name: /klasör seç/i });
    const style = getComputedStyle(button);

    expect(parseFloat(style.height)).toBeGreaterThanOrEqual(44);
    expect(style.borderRadius).toBe('8px');
    expect(style.backgroundColor).toBe('rgb(37, 99, 235)');
    expect(style.color).toBe('rgb(255, 255, 255)');
  });

  // AC-3: backend hazır değilken buton devre dışı görünümde olmalı.
  it('renders the disabled "Klasör Seç" button with a muted, not-allowed style (AC-3)', () => {
    render(<OnboardingScreen backendStatus="starting" onContinue={vi.fn()} />);

    const button = screen.getByRole('button', { name: /klasör seç/i });
    const style = getComputedStyle(button);

    expect(button).toBeDisabled();
    expect(style.backgroundColor).toBe('rgb(148, 163, 184)');
    expect(style.cursor).toBe('not-allowed');
  });
});

// AC-5: #2563EB arka plan + beyaz metin, WCAG AA (>=4.5:1) kontrast oranını karşılamalı.
describe('primary button color contrast (AC-5)', () => {
  function relativeLuminance([r, g, b]: [number, number, number]): number {
    const [rs, gs, bs] = [r, g, b].map((channel) => {
      const c = channel / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  }

  function contrastRatio(rgb1: [number, number, number], rgb2: [number, number, number]): number {
    const l1 = relativeLuminance(rgb1);
    const l2 = relativeLuminance(rgb2);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  it('meets WCAG AA contrast (>=4.5:1) for white text on #2563EB', () => {
    const background: [number, number, number] = [0x25, 0x63, 0xeb];
    const text: [number, number, number] = [255, 255, 255];

    expect(contrastRatio(background, text)).toBeGreaterThanOrEqual(4.5);
  });
});

// AC-1/AC-2: istek metin kutusu (textarea) render, stil ve controlled-state doğrulaması.
describe('request textarea (onboarding-istek-metin-kutusu)', () => {
  it('renders a textarea with min-height 120px, border-radius 12px, and #E5E7EB border (AC-1)', () => {
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    const textarea = screen.getByTestId('request-textarea');
    const style = getComputedStyle(textarea);

    expect(textarea).toBeInTheDocument();
    expect(parseFloat(style.minHeight)).toBeGreaterThanOrEqual(120);
    expect(style.borderRadius).toBe('12px');
    expect(style.borderColor).toBe('rgb(229, 231, 235)');
  });

  it('reflects typed text in the textarea value as a controlled component (AC-2)', () => {
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    const textarea = screen.getByTestId('request-textarea') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'bu klasördeki PDF\'leri tarihe göre sırala' } });

    expect(textarea.value).toBe('bu klasördeki PDF\'leri tarihe göre sırala');
  });
});

// AC-1..AC-3 (onboarding-istek-placeholder / Saga #254): placeholder metni, rengi ve
// yazınca kaybolma/silince geri gelme native davranışı.
describe('request textarea placeholder (onboarding-istek-placeholder)', () => {
  it('shows the guiding placeholder text with a muted #9CA3AF color when empty (AC-1)', () => {
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    const textarea = screen.getByTestId('request-textarea') as HTMLTextAreaElement;

    expect(textarea.placeholder).toBe('Bu klasördeki PDF\'leri tarihe göre sırala');
    expect(textarea.value).toBe('');
  });

  it('keeps the placeholder attribute intact while the user types — the browser hides it natively (AC-2)', () => {
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    const textarea = screen.getByTestId('request-textarea') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'bir istek yazıyorum' } });

    expect(textarea.value).toBe('bir istek yazıyorum');
    expect(textarea.placeholder).toBe('Bu klasördeki PDF\'leri tarihe göre sırala');
  });

  it('clears the typed value back to empty so the placeholder is visible again (AC-3)', () => {
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    const textarea = screen.getByTestId('request-textarea') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'bir istek' } });
    fireEvent.change(textarea, { target: { value: '' } });

    expect(textarea.value).toBe('');
    expect(textarea.placeholder).toBe('Bu klasördeki PDF\'leri tarihe göre sırala');
  });
});

// AC-1: uzun bir yol seçiliyken CSS tabanlı tek satır kesme uygulanmalı.
describe('selected-folder-path CSS truncation (AC-1, AC-4)', () => {
  it('applies single-line CSS ellipsis truncation to a long selected folder path (AC-1)', async () => {
    openFolderDialog.mockResolvedValue(
      'C:\\Users\\Yusuf\\Documents\\Müvekkiller\\2026\\Dava Dosyaları\\Deliller\\Alt Klasör\\Çok Uzun Bir Klasör Adı',
    );
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    const pathElement = await screen.findByTestId('selected-folder-path');
    const style = getComputedStyle(pathElement);

    expect(style.whiteSpace).toBe('nowrap');
    expect(style.overflow).toBe('hidden');
    expect(style.textOverflow).toBe('ellipsis');
  });

  it('renders the full path text content for a short selected folder path without truncation (AC-4)', async () => {
    openFolderDialog.mockResolvedValue('C:\\Kısa');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    const pathElement = await screen.findByTestId('selected-folder-path');

    expect(pathElement).toHaveTextContent('C:\\Kısa');
  });
});

// AC-1..AC-6 (bos-istek-engelleme / Saga #255): boş/whitespace istek gönderimi
// engellenmeli, alan içi #DC2626 kenarlık + hata mesajı gösterilmeli.
describe('empty request validation (bos-istek-engelleme)', () => {
  async function renderWithFolderSelected(onContinue = vi.fn()) {
    openFolderDialog.mockResolvedValue('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
    render(<OnboardingScreen backendStatus="ready" onContinue={onContinue} />);
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));
    await screen.findByTestId('selected-folder-path');
    return { onContinue };
  }

  it('shows no error and calls onContinue when the request text is non-empty (AC-1)', async () => {
    const { onContinue } = await renderWithFolderSelected();
    const textarea = screen.getByTestId('request-textarea');
    fireEvent.change(textarea, { target: { value: 'Bu klasördeki PDF\'leri tarihe göre sırala' } });

    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    expect(screen.queryByText('Devam etmek için bir istek yazın.')).not.toBeInTheDocument();
    expect(textarea).not.toHaveClass('has-error');
    await waitFor(() => expect(onContinue).toHaveBeenCalledTimes(1));
  });

  it('shows a red border and inline error, and does not call onContinue when the request is empty (AC-2)', async () => {
    const { onContinue } = await renderWithFolderSelected();

    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    const textarea = screen.getByTestId('request-textarea');
    expect(getComputedStyle(textarea).borderColor).toBe('rgb(220, 38, 38)');
    expect(screen.getByText('Devam etmek için bir istek yazın.')).toBeVisible();
    expect(onContinue).not.toHaveBeenCalled();
  });

  it('treats whitespace-only text the same as empty (AC-3)', async () => {
    const { onContinue } = await renderWithFolderSelected();
    const textarea = screen.getByTestId('request-textarea');
    fireEvent.change(textarea, { target: { value: '   \n\t  ' } });

    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    expect(getComputedStyle(textarea).borderColor).toBe('rgb(220, 38, 38)');
    expect(screen.getByText('Devam etmek için bir istek yazın.')).toBeVisible();
    expect(onContinue).not.toHaveBeenCalled();
  });

  it('clears the error as soon as the user types non-empty content (AC-4)', async () => {
    await renderWithFolderSelected();
    const textarea = screen.getByTestId('request-textarea');
    fireEvent.click(screen.getByRole('button', { name: /devam/i }));
    expect(screen.getByText('Devam etmek için bir istek yazın.')).toBeVisible();

    fireEvent.change(textarea, { target: { value: 'artık boş değil' } });

    expect(screen.queryByText('Devam etmek için bir istek yazın.')).not.toBeInTheDocument();
    expect(getComputedStyle(textarea).borderColor).not.toBe('rgb(220, 38, 38)');
  });

  it('renders the error message inside an aria-live="polite" region (AC-5)', async () => {
    await renderWithFolderSelected();
    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    const message = screen.getByText('Devam etmek için bir istek yazın.');
    expect(message.closest('[aria-live="polite"]')).not.toBeNull();
  });

  it('re-shows the error if the user clears the field again and resubmits (AC-6)', async () => {
    await renderWithFolderSelected();
    const textarea = screen.getByTestId('request-textarea');
    fireEvent.click(screen.getByRole('button', { name: /devam/i }));
    fireEvent.change(textarea, { target: { value: 'geçici metin' } });
    fireEvent.change(textarea, { target: { value: '   ' } });

    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    expect(screen.getByText('Devam etmek için bir istek yazın.')).toBeVisible();
  });
});

// AC-1..AC-5 (gecersiz-klasor-reddi / Saga #256): geçersiz/erişilemeyen klasör
// seçimi reddedilmeli, seçim korunmalı, alan içi hata mesajı gösterilmeli.
describe('invalid folder rejection (gecersiz-klasor-reddi)', () => {
  it('shows no error and enables Continue when the selected folder is accessible (AC-1)', async () => {
    invokeTauriCommand.mockResolvedValue(true);
    openFolderDialog.mockResolvedValue('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    expect(await screen.findByTestId('selected-folder-path')).toHaveTextContent('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
    expect(invokeTauriCommand).toHaveBeenCalledWith('plugin:fs|exists', { path: 'C:\\Users\\Yusuf\\Documents\\Müvekkiller' });
    expect(screen.queryByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /devam/i })).toBeEnabled();
  });

  it('disables Continue while a newly-selected folder\'s accessibility check is still pending, even if the previous folder was valid (TOCTOU koruması)', async () => {
    invokeTauriCommand.mockResolvedValue(true);
    openFolderDialog.mockResolvedValue('C:\\Geçerli1');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /devam/i })).toBeEnabled());

    let resolveExists: (value: boolean) => void = () => {};
    invokeTauriCommand.mockReturnValue(new Promise((resolve) => { resolveExists = resolve; }));
    openFolderDialog.mockResolvedValue('C:\\YavaşAğPaylaşımı');
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    await waitFor(() => {
      expect(screen.getByTestId('selected-folder-path')).toHaveTextContent('C:\\YavaşAğPaylaşımı');
    });
    expect(screen.getByRole('button', { name: /devam/i })).toBeDisabled();

    resolveExists(true);
    await waitFor(() => expect(screen.getByRole('button', { name: /devam/i })).toBeEnabled());
  });

  it('keeps the path visible, shows a red error, and disables Continue when the folder is inaccessible (AC-2)', async () => {
    invokeTauriCommand.mockResolvedValue(false);
    openFolderDialog.mockResolvedValue('C:\\Users\\Yusuf\\Documents\\Silinmiş');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    const pathElement = await screen.findByTestId('selected-folder-path');
    expect(pathElement).toHaveTextContent('C:\\Users\\Yusuf\\Documents\\Silinmiş');
    const message = await screen.findByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.');
    expect(getComputedStyle(message).color).toBe('rgb(220, 38, 38)');
    expect(screen.getByRole('button', { name: /devam/i })).toBeDisabled();
  });

  it('clears the error and re-enables Continue after selecting a valid folder (AC-3)', async () => {
    invokeTauriCommand.mockResolvedValue(false);
    openFolderDialog.mockResolvedValue('C:\\Geçersiz');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));
    await screen.findByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.');

    invokeTauriCommand.mockResolvedValue(true);
    openFolderDialog.mockResolvedValue('C:\\Geçerli');
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    await waitFor(() => {
      expect(screen.queryByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.')).not.toBeInTheDocument();
    });
    expect(screen.getByTestId('selected-folder-path')).toHaveTextContent('C:\\Geçerli');
    expect(screen.getByRole('button', { name: /devam/i })).toBeEnabled();
  });

  it('strips a trailing slash/backslash from the selected path (AC-4)', async () => {
    invokeTauriCommand.mockResolvedValue(true);
    openFolderDialog.mockResolvedValue('C:\\Users\\Yusuf\\Belgeler\\');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    expect(await screen.findByTestId('selected-folder-path')).toHaveTextContent('C:\\Users\\Yusuf\\Belgeler');
    expect(invokeTauriCommand).toHaveBeenCalledWith('plugin:fs|exists', { path: 'C:\\Users\\Yusuf\\Belgeler' });
  });

  it('re-shows the error on each consecutive inaccessible folder selection (AC-5)', async () => {
    invokeTauriCommand.mockResolvedValue(false);
    openFolderDialog.mockResolvedValue('C:\\Geçersiz1');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));
    await screen.findByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.');

    openFolderDialog.mockResolvedValue('C:\\Geçersiz2');
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    // Yeni seçimde hata anlık olarak temizlenip doğrulama tamamlanınca yeniden gösterilir
    // (TOCTOU koruması) — önce path güncellemesini bekleyip stale element'i eleyerek
    // hatanın gerçekten YENİDEN göründüğünü doğruluyoruz, ilk (eski) eşleşmeyi değil.
    await waitFor(() => {
      expect(screen.getByTestId('selected-folder-path')).toHaveTextContent('C:\\Geçersiz2');
    });
    await waitFor(() => {
      expect(screen.getByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.')).toBeVisible();
    });
  });

  it('treats a rejected invoke call as inaccessible instead of failing silently (behavior contract row 8)', async () => {
    invokeTauriCommand.mockRejectedValue(new Error('IPC hatası'));
    openFolderDialog.mockResolvedValue('C:\\Beklenmedik');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));

    expect(await screen.findByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.')).toBeVisible();
    expect(screen.getByRole('button', { name: /devam/i })).toBeDisabled();
  });
});

// AC-2..AC-5 (klavye-ile-form-gezintisi / Saga #257): Enter ile gönderim ve
// hata sonrası odak taşıma. AC-1 (tam Tab sırası) ve AC-3'ün "Devam" butonu
// kısmı ile AC-6 (native buton Enter davranışı) jsdom'da güvenilir simüle
// edilemediği için sadece e2e'de test ediliyor (bkz. plan.md).
describe('keyboard navigation and focus management (klavye-ile-form-gezintisi)', () => {
  async function renderWithValidFolder(onContinue = vi.fn()) {
    invokeTauriCommand.mockResolvedValue(true);
    openFolderDialog.mockResolvedValue('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
    render(<OnboardingScreen backendStatus="ready" onContinue={onContinue} />);
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));
    await screen.findByTestId('selected-folder-path');
    return { onContinue };
  }

  it('does not submit and inserts a normal newline when Enter is pressed inside the textarea (AC-2)', async () => {
    const { onContinue } = await renderWithValidFolder();
    const textarea = screen.getByTestId('request-textarea');

    fireEvent.keyDown(textarea, { key: 'Enter' });

    expect(onContinue).not.toHaveBeenCalled();
    expect(screen.queryByText('Devam etmek için bir istek yazın.')).not.toBeInTheDocument();
  });

  it('calls onContinue when Enter is pressed on the selected-folder-path element and the form is valid (AC-3)', async () => {
    const { onContinue } = await renderWithValidFolder();
    fireEvent.change(screen.getByTestId('request-textarea'), { target: { value: 'bu klasördeki PDF\'leri sırala' } });

    fireEvent.keyDown(screen.getByTestId('selected-folder-path'), { key: 'Enter' });

    await waitFor(() => expect(onContinue).toHaveBeenCalledTimes(1));
  });

  it('shows the empty-request error and moves focus to the textarea when Enter is pressed on an invalid form (AC-4)', async () => {
    const { onContinue } = await renderWithValidFolder();

    fireEvent.keyDown(screen.getByTestId('selected-folder-path'), { key: 'Enter' });

    expect(onContinue).not.toHaveBeenCalled();
    expect(screen.getByText('Devam etmek için bir istek yazın.')).toBeVisible();
    expect(document.activeElement).toBe(screen.getByTestId('request-textarea'));
  });

  it('moves focus to the textarea when Continue is clicked on an invalid form (AC-4, tıklama)', async () => {
    await renderWithValidFolder();

    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    expect(document.activeElement).toBe(screen.getByTestId('request-textarea'));
  });

  it('moves focus to the "Klasör Seç" button after selecting an inaccessible folder (AC-5)', async () => {
    invokeTauriCommand.mockResolvedValue(false);
    openFolderDialog.mockResolvedValue('C:\\Users\\Yusuf\\Documents\\Silinmiş');
    render(<OnboardingScreen backendStatus="ready" onContinue={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));
    await screen.findByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.');

    expect(document.activeElement).toBe(screen.getByRole('button', { name: /klasör seç/i }));
  });

  it('does not call onContinue when Enter is pressed on selected-folder-path while the folder is invalid, even with non-empty request text (red-team: doğrulama atlatma düzeltmesi)', async () => {
    invokeTauriCommand.mockResolvedValue(false);
    openFolderDialog.mockResolvedValue('C:\\Users\\Yusuf\\Documents\\Silinmiş');
    const onContinue = vi.fn();
    render(<OnboardingScreen backendStatus="ready" onContinue={onContinue} />);
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));
    await screen.findByText('Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.');
    fireEvent.change(screen.getByTestId('request-textarea'), { target: { value: 'geçerli bir istek metni' } });

    fireEvent.keyDown(screen.getByTestId('selected-folder-path'), { key: 'Enter' });

    expect(onContinue).not.toHaveBeenCalled();
  });
});

// AC-1..AC-4 (ilk-istek-oturum-baglami / Saga #258): geçerli formda "Devam"
// gerçekten backend'e POST /api/session gönderiyor; başarı, hata ve
// çift-gönderim senaryoları.
describe('session submission (ilk-istek-oturum-baglami)', () => {
  async function renderReadyToSubmit(onContinue = vi.fn()) {
    invokeTauriCommand.mockResolvedValue(true);
    openFolderDialog.mockResolvedValue('C:\\Users\\Yusuf\\Documents\\Müvekkiller');
    render(<OnboardingScreen backendStatus="ready" onContinue={onContinue} />);
    fireEvent.click(screen.getByRole('button', { name: /klasör seç/i }));
    await screen.findByTestId('selected-folder-path');
    fireEvent.change(screen.getByTestId('request-textarea'), { target: { value: 'PDF\'leri tarihe göre sırala' } });
    return { onContinue };
  }

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('POSTs the selected folder and request text to /api/session and calls onContinue on success (AC-1)', async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ sessionId: '11111111-1111-1111-1111-111111111111', selectedFolder: 'C:\\Users\\Yusuf\\Documents\\Müvekkiller', requestText: 'PDF\'leri tarihe göre sırala' }),
    } as Response);
    const { onContinue } = await renderReadyToSubmit();

    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    await waitFor(() => expect(onContinue).toHaveBeenCalledTimes(1));
    expect(mockFetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/session',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ selectedFolder: 'C:\\Users\\Yusuf\\Documents\\Müvekkiller', requestText: 'PDF\'leri tarihe göre sırala' }),
      }),
    );
  });

  it('shows a submit error and does not call onContinue when the backend rejects the request (AC-2)', async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue({ ok: false, json: async () => ({ detail: 'invalid' }) } as Response);
    const { onContinue } = await renderReadyToSubmit();

    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    expect(await screen.findByText('İstek gönderilemedi. Lütfen tekrar deneyin.')).toBeVisible();
    expect(onContinue).not.toHaveBeenCalled();
  });

  it('shows a submit error and does not call onContinue when the network request fails (AC-3)', async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockRejectedValue(new Error('network error'));
    const { onContinue } = await renderReadyToSubmit();

    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    expect(await screen.findByText('İstek gönderilemedi. Lütfen tekrar deneyin.')).toBeVisible();
    expect(onContinue).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /devam/i })).toBeEnabled();
  });

  it('disables Continue while the request is in flight to prevent a double submit (AC-4)', async () => {
    const mockFetch = vi.mocked(fetch);
    let resolveFetch: (value: Response) => void = () => {};
    mockFetch.mockReturnValue(new Promise<Response>((resolve) => { resolveFetch = resolve; }));
    await renderReadyToSubmit();

    fireEvent.click(screen.getByRole('button', { name: /devam/i }));

    expect(screen.getByRole('button', { name: /devam/i })).toBeDisabled();

    resolveFetch({ ok: true, json: async () => ({ sessionId: '1', selectedFolder: 'x', requestText: 'y' }) } as Response);
    await waitFor(() => expect(screen.getByRole('button', { name: /devam/i })).toBeEnabled());
  });
});
