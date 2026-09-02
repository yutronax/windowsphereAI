import { describe, expect, it } from 'vitest';

import { tokens } from './tokens';

describe('tokens (design-tokens-foundation / Saga #345)', () => {
  it('exports all inventoried colors with their exact values (AC-1)', () => {
    expect(tokens.colors.primary).toBe('#1E3A8A');
    expect(tokens.colors.primaryHover).toBe('#1E3172');
    expect(tokens.colors.primaryActive).toBe('#172554');
    expect(tokens.colors.border).toBe('#E5E7EB');
    expect(tokens.colors.danger).toBe('#DC2626');
    expect(tokens.colors.textSecondary).toBe('#4B5563');
    expect(tokens.colors.textMuted).toBe('#6B7280');
    expect(tokens.colors.textDark).toBe('#111827');
    expect(tokens.colors.panelBackground).toBe('#F3F4F6');
  });

  it('exports all inventoried spacing/typography values with their exact values (AC-1)', () => {
    expect(tokens.radius.default).toBe('8px');
    expect(tokens.size.buttonHeight).toBe('44px');
    expect(tokens.fontSize.small).toBe('14px');
    expect(tokens.fontSize.base).toBe('16px');
    expect(tokens.spacing.buttonPadding).toBe('0 20px');
  });

  it('has no missing (undefined) token in colors, radius, size, fontSize or spacing (AC-2)', () => {
    for (const group of [tokens.colors, tokens.radius, tokens.size, tokens.fontSize, tokens.spacing]) {
      for (const [key, value] of Object.entries(group)) {
        expect(value, `token "${key}" is missing`).toBeDefined();
        expect(value, `token "${key}" is empty`).not.toBe('');
      }
    }
  });

  // AC-5: New danger/success color variants for ChatScreen visual improvements
  // (plan-error-indicator: dangerBannerBg/dangerBannerBorder/dangerBannerText)
  it('exports dangerBannerBg, dangerBannerBorder, dangerBannerText with their exact values (AC-5, plan-error-indicator)', () => {
    expect(tokens.colors.dangerBannerBg).toBe('#FEF2F2');
    expect(tokens.colors.dangerBannerBorder).toBe('#FCA5A5');
    expect(tokens.colors.dangerBannerText).toBe('#B91C1C');
  });

  // AC-5: New danger variants for clear-history error message
  // (chat-clear-history-error-message: dangerMessageBg/dangerMessageBorder/dangerMessageText)
  it('exports dangerMessageBg, dangerMessageBorder, dangerMessageText with their exact values (AC-5, clear-history-error-message)', () => {
    expect(tokens.colors.dangerMessageBg).toBe('#FEE2E2');
    expect(tokens.colors.dangerMessageBorder).toBe('#FECACA');
    expect(tokens.colors.dangerMessageText).toBe('#991B1B');
  });

  // AC-5: New success color variants for clear-history success message
  // (chat-clear-history-success-message: successBg/successBorder/successText)
  it('exports successBg, successBorder, successText with their exact values (AC-5, clear-history-success-message)', () => {
    expect(tokens.colors.successBg).toBe('#D1FAE5');
    expect(tokens.colors.successBorder).toBe('#A7F3D0');
    expect(tokens.colors.successText).toBe('#065F46');
  });

  // AC-4: New connected status color token for TransactionHistoryPanel
  it('exports connected color with its exact value (AC-4, connection-status)', () => {
    expect(tokens.colors.connected).toBe('#059669');
  });

  it('exports white color with its exact value (AC-1, ChatScreen ham hex temizliği)', () => {
    expect(tokens.colors.white).toBe('#fff');
  });
});
