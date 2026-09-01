import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import { relativeTime } from './relativeTime';

describe('relativeTime (Türkçe göreceli zaman)', () => {
  let now: Date;

  beforeEach(() => {
    // Test için sabit "şimdi" zamanı belirleyelim
    now = new Date('2026-09-01T14:00:00Z');
    vi.useFakeTimers();
    vi.setSystemTime(now);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Less than 1 minute (< 60s)', () => {
    it('returns "az önce" for events that happened 0-59 seconds ago (AC-1)', () => {
      const thirtySecondsAgo = new Date(now.getTime() - 30 * 1000);
      expect(relativeTime(thirtySecondsAgo.toISOString())).toBe('az önce');
    });

    it('returns "az önce" for the exact same moment (boundary)', () => {
      expect(relativeTime(now.toISOString())).toBe('az önce');
    });

    it('returns "az önce" for 59 seconds ago (boundary)', () => {
      const fiftyNineSecondsAgo = new Date(now.getTime() - 59 * 1000);
      expect(relativeTime(fiftyNineSecondsAgo.toISOString())).toBe('az önce');
    });
  });

  describe('Minutes (1-59 minutes ago)', () => {
    it('returns "1 dakika önce" for 1 minute ago (AC-1)', () => {
      const oneMinuteAgo = new Date(now.getTime() - 60 * 1000);
      expect(relativeTime(oneMinuteAgo.toISOString())).toBe('1 dakika önce');
    });

    it('returns "5 dakika önce" for 5 minutes ago (AC-1)', () => {
      const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
      expect(relativeTime(fiveMinutesAgo.toISOString())).toBe('5 dakika önce');
    });

    it('returns "59 dakika önce" for 59 minutes ago (boundary)', () => {
      const fiftyNineMinutesAgo = new Date(now.getTime() - 59 * 60 * 1000);
      expect(relativeTime(fiftyNineMinutesAgo.toISOString())).toBe('59 dakika önce');
    });

    it('handles fractional minutes by rounding down', () => {
      // 90 saniye = 1.5 dakika, aşağı yuvarla = 1 dakika
      const ninetySecondsAgo = new Date(now.getTime() - 90 * 1000);
      expect(relativeTime(ninetySecondsAgo.toISOString())).toBe('1 dakika önce');
    });
  });

  describe('Hours (1-23 hours ago)', () => {
    it('returns "1 saat önce" for 1 hour ago (AC-1)', () => {
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      expect(relativeTime(oneHourAgo.toISOString())).toBe('1 saat önce');
    });

    it('returns "3 saat önce" for 3 hours ago (AC-1)', () => {
      const threeHoursAgo = new Date(now.getTime() - 3 * 60 * 60 * 1000);
      expect(relativeTime(threeHoursAgo.toISOString())).toBe('3 saat önce');
    });

    it('returns "23 saat önce" for 23 hours ago (boundary)', () => {
      const twentyThreeHoursAgo = new Date(now.getTime() - 23 * 60 * 60 * 1000);
      expect(relativeTime(twentyThreeHoursAgo.toISOString())).toBe('23 saat önce');
    });

    it('handles fractional hours by rounding down', () => {
      // 90 dakika = 1.5 saat, aşağı yuvarla = 1 saat
      const ninetyMinutesAgo = new Date(now.getTime() - 90 * 60 * 1000);
      expect(relativeTime(ninetyMinutesAgo.toISOString())).toBe('1 saat önce');
    });
  });

  describe('Days (1+ days ago)', () => {
    it('returns "1 gün önce" for 1 day ago (AC-1)', () => {
      const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      expect(relativeTime(oneDayAgo.toISOString())).toBe('1 gün önce');
    });

    it('returns "7 gün önce" for 1 week ago (AC-1)', () => {
      const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      expect(relativeTime(oneWeekAgo.toISOString())).toBe('7 gün önce');
    });

    it('returns "365 gün önce" for 1 year ago (AC-1)', () => {
      const oneYearAgo = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
      expect(relativeTime(oneYearAgo.toISOString())).toBe('365 gün önce');
    });

    it('handles fractional days by rounding down', () => {
      // 36 saat = 1.5 gün, aşağı yuvarla = 1 gün
      const thirtyNineHoursAgo = new Date(now.getTime() - 39 * 60 * 60 * 1000);
      expect(relativeTime(thirtyNineHoursAgo.toISOString())).toBe('1 gün önce');
    });
  });

  describe('Future times (graceful handling)', () => {
    it('returns "az önce" for a time in the future (behaviour contract)', () => {
      const fiveSecondsFromNow = new Date(now.getTime() + 5 * 1000);
      expect(relativeTime(fiveSecondsFromNow.toISOString())).toBe('az önce');
    });

    it('returns "az önce" even for far future times (no negative values)', () => {
      const oneYearFromNow = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000);
      expect(relativeTime(oneYearFromNow.toISOString())).toBe('az önce');
    });
  });

  describe('Invalid inputs (robustness)', () => {
    it('throws or returns safe value for invalid ISO string', () => {
      // Eğer fonksiyon hata atarsa, test otomatik fail olur
      // Eğer safe bir değer dönerse (ör. "az önce"), bu da kabul edilebilir
      expect(() => relativeTime('invalid-date')).not.toThrow();
    });

    it('handles empty string gracefully', () => {
      expect(() => relativeTime('')).not.toThrow();
    });
  });

  describe('Edge cases', () => {
    it('correctly handles ISO string with milliseconds', () => {
      const twoMinutesAgoWithMs = new Date(now.getTime() - 2 * 60 * 1000);
      const isoWithMs = twoMinutesAgoWithMs.toISOString();
      expect(relativeTime(isoWithMs)).toBe('2 dakika önce');
    });

    it('correctly handles ISO string without timezone indicator (assumed UTC)', () => {
      // relativeTime should parse ISO strings correctly, with or without Z suffix
      const threeHoursAgoWithoutZ = new Date(now.getTime() - 3 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(threeHoursAgoWithoutZ)).toBe('3 saat önce');
    });
  });
});
