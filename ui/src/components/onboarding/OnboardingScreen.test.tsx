import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { open } from '@tauri-apps/plugin-dialog';

import OnboardingScreen, { truncateWindowsPath } from './OnboardingScreen';

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
});

describe('truncateWindowsPath', () => {
  it('shortens an overlong Windows path with an ellipsis while preserving its final folder', () => {
    const path = 'C:\\Users\\Yusuf\\Documents\\Müvekkiller\\2026\\Dava Dosyaları\\Deliller';
    const shortened = truncateWindowsPath(path, 40);

    expect(shortened).toContain('…');
    expect(shortened).toEndWith('\\Deliller');
    expect(shortened.length).toBeLessThanOrEqual(40);
  });
});
