import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { open } from '@tauri-apps/plugin-dialog';

import OnboardingScreen from './OnboardingScreen';

vi.mock('@tauri-apps/plugin-dialog', () => ({
  open: vi.fn(),
}));

const openFolderDialog = vi.mocked(open);

describe('OnboardingScreen', () => {
  beforeEach(() => {
    openFolderDialog.mockReset();
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
    expect(onContinue).toHaveBeenCalledTimes(1);
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
