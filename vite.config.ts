import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['ui/src/**/*.test.{ts,tsx}'],
    setupFiles: ['./ui/src/setupTests.ts'],
    globals: true,
    // Saga #334: `vi.useFakeTimers()` (SearchPanel.test.tsx'in AC-2/3
    // testleri) kullanılırken React 18'in scheduler'ı (MessageChannel /
    // gerçek makro-görev kuyruğuna dayanır) ve @testing-library'nin
    // `waitFor`'unun mikro görev boşaltma adımı ilerleyemiyor, testler
    // sonsuza kadar asılı kalıyordu. `shouldAdvanceTime: true` sahte
    // saatin gerçek zamanla orantılı ilerlemesini sağlayarak bu
    // zamanlayıcıların normal şekilde tetiklenmesine izin verir.
    fakeTimers: { shouldAdvanceTime: true },
  },
});
