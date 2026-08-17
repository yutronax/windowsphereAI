import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';

// OnboardingScreen'in kendi mantığı (klasör seçimi, validasyon, /api/session
// çağrısı) kendi test dosyasında (OnboardingScreen.test.tsx) zaten kapsanıyor.
// Burada sadece App.tsx'in onContinue prop'unu doğru bağladığını (ana sohbet
// ekranına geçiş) dar bir kapsamda doğruluyoruz — bu yüzden bileşen mock'lanıyor.
vi.mock('./components/onboarding/OnboardingScreen', () => ({
  default: ({ onContinue }: { onContinue: (sessionId: string) => void }) => (
    <button onClick={() => onContinue('11111111-1111-1111-1111-111111111111')}>mock-onboarding-continue</button>
  ),
}));

describe('App (ilk-istek-oturum-baglami / Saga #258)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
  });

  it('shows the main chat screen once OnboardingScreen signals a successful session (AC-1)', async () => {
    render(<App />);

    fireEvent.click(await screen.findByText('mock-onboarding-continue'));

    expect(await screen.findByTestId('main-chat-screen')).toBeVisible();
  });
});

describe('App — gerçek /api/plan bağlantısı (Saga #287)', () => {
  async function renderChatScreen(fetchMock: ReturnType<typeof vi.fn>) {
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);
    fireEvent.click(await screen.findByText('mock-onboarding-continue'));
    await screen.findByTestId('main-chat-screen');
    return fetchMock;
  }

  it('calls POST /api/plan with the sessionId and shows the returned plan (AC-3)', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/api/config')) return Promise.resolve({ ok: false });
      if (url.endsWith('/api/plan')) {
        expect(JSON.parse(init!.body as string)).toEqual({ sessionId: '11111111-1111-1111-1111-111111111111' });
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              steps: [{ order: 0, operationType: 'Taşı', targetFolder: '2026-08', affectedFileCount: 1 }],
            }),
        });
      }
      return Promise.resolve({ ok: false });
    });
    await renderChatScreen(fetchMock);

    fireEvent.change(screen.getByTestId('chat-input-textarea'), { target: { value: 'PDF\'leri sırala' } });
    fireEvent.click(screen.getByText('Gönder'));

    expect(await screen.findByTestId('plan-card')).toBeVisible();
    expect(screen.getByTestId('plan-approve-button')).toBeEnabled();
  });

  it('sets planError and shows the retry UI when /api/plan fails (AC-4)', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/api/config')) return Promise.resolve({ ok: false });
      if (url.endsWith('/api/plan')) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Oturum bulunamadı' }) });
      }
      return Promise.resolve({ ok: false });
    });
    await renderChatScreen(fetchMock);

    fireEvent.change(screen.getByTestId('chat-input-textarea'), { target: { value: 'PDF\'leri sırala' } });
    fireEvent.click(screen.getByText('Gönder'));

    const indicator = await screen.findByTestId('plan-error-indicator');
    expect(indicator).toHaveTextContent('Oturum bulunamadı');
  });

  it('retries the same request when "Tekrar dene" is clicked after a failure (AC-4)', async () => {
    let planCallCount = 0;
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/api/config')) return Promise.resolve({ ok: false });
      if (url.endsWith('/api/plan')) {
        planCallCount += 1;
        if (planCallCount === 1) {
          return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'geçici hata' }) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ steps: [] }) });
      }
      return Promise.resolve({ ok: false });
    });
    await renderChatScreen(fetchMock);

    fireEvent.change(screen.getByTestId('chat-input-textarea'), { target: { value: 'PDF\'leri sırala' } });
    fireEvent.click(screen.getByText('Gönder'));
    await screen.findByTestId('plan-error-indicator');

    fireEvent.click(screen.getByTestId('plan-retry-button'));

    await screen.findByText('Seçili klasörde işlenecek PDF bulunamadı.');
    expect(planCallCount).toBe(2);
  });

  it('shows a planError and does not render PlanCard when the 200 response fails runtime plan validation (Saga #281)', async () => {
    // Saga #262/#280 bulgusu: backend'den 2xx gelse bile plan verisi
    // hiçbir runtime doğrulaması olmadan render edilmemeli — geçersiz bir
    // operationType (KNOWN_OPERATION_TYPES'ta olmayan) planCard'ı DEĞİL,
    // planError'ı tetiklemeli.
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/api/config')) return Promise.resolve({ ok: false });
      if (url.endsWith('/api/plan')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              steps: [{ order: 0, operationType: 'BilinmeyenTür', targetFolder: '2026-08', affectedFileCount: 1 }],
            }),
        });
      }
      return Promise.resolve({ ok: false });
    });
    await renderChatScreen(fetchMock);

    fireEvent.change(screen.getByTestId('chat-input-textarea'), { target: { value: 'PDF\'leri sırala' } });
    fireEvent.click(screen.getByText('Gönder'));

    const indicator = await screen.findByTestId('plan-error-indicator');
    expect(indicator).toHaveTextContent('Sunucudan geçersiz plan verisi alındı');
    expect(screen.queryByTestId('plan-card')).not.toBeInTheDocument();
  });

  it('respects an explicit "rejected" securityStatus from the backend instead of overriding it (Saga #281 red-team fix)', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/api/config')) return Promise.resolve({ ok: false });
      if (url.endsWith('/api/plan')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              steps: [{ order: 0, operationType: 'Taşı', targetFolder: '2026-08', affectedFileCount: 1 }],
              securityStatus: 'rejected',
              rejectionReason: 'Güvenlik taramasından geçemedi',
            }),
        });
      }
      return Promise.resolve({ ok: false });
    });
    await renderChatScreen(fetchMock);

    fireEvent.change(screen.getByTestId('chat-input-textarea'), { target: { value: 'PDF\'leri sırala' } });
    fireEvent.click(screen.getByText('Gönder'));

    await screen.findByTestId('plan-rejection-reason');
    expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
  });

  it('does not call any apply/orchestrator endpoint when a plan is approved (AC-5)', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/api/config')) return Promise.resolve({ ok: false });
      if (url.endsWith('/api/plan')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              steps: [{ order: 0, operationType: 'Taşı', targetFolder: '2026-08', affectedFileCount: 1 }],
            }),
        });
      }
      return Promise.resolve({ ok: false });
    });
    await renderChatScreen(fetchMock);
    fireEvent.change(screen.getByTestId('chat-input-textarea'), { target: { value: 'PDF\'leri sırala' } });
    fireEvent.click(screen.getByText('Gönder'));
    await screen.findByTestId('plan-approve-button');
    fetchMock.mockClear();

    fireEvent.click(screen.getByTestId('plan-approve-button'));

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
