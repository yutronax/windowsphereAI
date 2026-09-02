import { beforeEach, describe, expect, it, vi } from 'vitest';
import { applyStoredTheme, getTheme, toggleTheme } from './theme';

// Saga #360: Dark/light theme support tests
describe('lib/theme — localStorage-based theme persistence (Saga #360)', () => {
  beforeEach(() => {
    // Clean up DOM state between tests
    document.documentElement.removeAttribute('data-theme');
    // Clear localStorage between tests
    localStorage.clear();
  });

  describe('applyStoredTheme()', () => {
    it('applies "light" theme from localStorage (AC-2, Davranış Sözleşmesi #4)', () => {
      localStorage.setItem('theme', 'light');
      applyStoredTheme();
      expect(document.documentElement.dataset.theme).toBe('light');
    });

    it('does not set data-theme when localStorage has "dark" (defaults to :root koyu tema) (AC-1, Davranış Sözleşmesi #1,5)', () => {
      localStorage.setItem('theme', 'dark');
      applyStoredTheme();
      expect(document.documentElement.dataset.theme).toBeUndefined();
    });

    it('does not set data-theme when localStorage is empty (AC-1, Davranış Sözleşmesi #1)', () => {
      applyStoredTheme();
      expect(document.documentElement.dataset.theme).toBeUndefined();
    });

    it('does not set data-theme when localStorage has an invalid value like "xyz" (AC-4, Davranış Sözleşmesi #5)', () => {
      localStorage.setItem('theme', 'xyz');
      applyStoredTheme();
      expect(document.documentElement.dataset.theme).toBeUndefined();
    });

    it('silently defaults to dark theme when localStorage.getItem raises an error (AC-4, Davranış Sözleşmesi #6)', () => {
      const getItemSpy = vi.spyOn(localStorage, 'getItem').mockImplementation(() => {
        throw new Error('localStorage access denied');
      });

      // Should not throw
      expect(() => applyStoredTheme()).not.toThrow();
      expect(document.documentElement.dataset.theme).toBeUndefined(); // Defaults to dark (no data-theme set)

      getItemSpy.mockRestore();
    });
  });

  describe('toggleTheme()', () => {
    it('toggles from dark (no data-theme) to light and writes "light" to localStorage (AC-2, Davranış Sözleşmesi #2)', () => {
      toggleTheme();
      expect(document.documentElement.dataset.theme).toBe('light');
      expect(localStorage.getItem('theme')).toBe('light');
    });

    it('toggles from light to dark (removes data-theme) and writes "dark" to localStorage (AC-2, Davranış Sözleşmesi #3)', () => {
      document.documentElement.dataset.theme = 'light';
      toggleTheme();
      expect(document.documentElement.dataset.theme).toBeUndefined();
      expect(localStorage.getItem('theme')).toBe('dark');
    });

    it('persists the toggle choice across browser reload by reading localStorage (AC-3)', () => {
      // First toggle: dark -> light
      toggleTheme();
      expect(localStorage.getItem('theme')).toBe('light');
      expect(document.documentElement.dataset.theme).toBe('light');

      // Simulate page reload by clearing DOM but preserving localStorage
      document.documentElement.removeAttribute('data-theme');

      // Re-apply stored theme (simulating App.tsx mount)
      applyStoredTheme();
      expect(document.documentElement.dataset.theme).toBe('light');

      // Second toggle: light -> dark
      toggleTheme();
      expect(localStorage.getItem('theme')).toBe('dark');
      expect(document.documentElement.dataset.theme).toBeUndefined();

      // Simulate page reload again
      document.documentElement.removeAttribute('data-theme');
      applyStoredTheme();
      expect(document.documentElement.dataset.theme).toBeUndefined();
    });
  });

  describe('getTheme()', () => {
    it('returns "dark" when data-theme is not set (AC-1)', () => {
      expect(getTheme()).toBe('dark');
    });

    it('returns "light" when data-theme="light" is set (AC-2)', () => {
      document.documentElement.dataset.theme = 'light';
      expect(getTheme()).toBe('light');
    });

    it('returns "dark" when data-theme is explicitly set to "dark" (Davranış Sözleşmesi #3)', () => {
      // Note: setting data-theme to "dark" explicitly is unusual (we use absence instead),
      // but this test ensures the function handles it correctly
      document.documentElement.dataset.theme = 'dark';
      expect(getTheme()).toBe('dark');
    });

    it('returns "dark" when data-theme has an unexpected value (defensive fallback)', () => {
      document.documentElement.dataset.theme = 'xyz';
      expect(getTheme()).toBe('dark');
    });
  });

  describe('integration: multiple toggles and reloads', () => {
    it('maintains theme state across multiple rapid toggles (AC-2, stress test)', () => {
      expect(getTheme()).toBe('dark');

      toggleTheme(); // dark -> light
      expect(getTheme()).toBe('light');

      toggleTheme(); // light -> dark
      expect(getTheme()).toBe('dark');

      toggleTheme(); // dark -> light
      expect(getTheme()).toBe('light');

      expect(localStorage.getItem('theme')).toBe('light');
    });

    it('correctly handles localStorage error during toggleTheme (AC-4)', () => {
      const setItemSpy = vi.spyOn(localStorage, 'setItem').mockImplementation(() => {
        throw new Error('localStorage quota exceeded');
      });

      // toggleTheme should not throw even if setItem fails
      expect(() => toggleTheme()).not.toThrow();
      // But DOM should still be updated
      expect(document.documentElement.dataset.theme).toBe('light');

      setItemSpy.mockRestore();
    });
  });
});
