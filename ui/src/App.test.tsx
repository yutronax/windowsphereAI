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
