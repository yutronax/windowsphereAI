import { describe, expect, it } from 'vitest';

import { tokens } from './tokens';

// Saga #360: colors group now uses CSS custom property references (var(--color-x)) for theme-aware theming
describe('tokens (design-tokens-foundation / Saga #345; updated Saga #360 for dark/light theme support)', () => {
  it('exports all inventoried colors as CSS custom property references (AC-1, Saga #360)', () => {
    expect(tokens.colors.primary).toBe('var(--color-primary)');
    expect(tokens.colors.primaryHover).toBe('var(--color-primary-hover)');
    expect(tokens.colors.primaryActive).toBe('var(--color-primary-active)');
    expect(tokens.colors.border).toBe('var(--color-border)');
    expect(tokens.colors.danger).toBe('var(--color-danger)');
    expect(tokens.colors.textSecondary).toBe('var(--color-text-secondary)');
    expect(tokens.colors.textMuted).toBe('var(--color-text-muted)');
    expect(tokens.colors.textDark).toBe('var(--color-text-dark)');
    expect(tokens.colors.panelBackground).toBe('var(--color-panel-background)');
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
  // Updated to CSS custom property references (Saga #360)
  it('exports dangerBannerBg, dangerBannerBorder, dangerBannerText as CSS custom property references (AC-5, plan-error-indicator, Saga #360)', () => {
    expect(tokens.colors.dangerBannerBg).toBe('var(--color-danger-banner-bg)');
    expect(tokens.colors.dangerBannerBorder).toBe('var(--color-danger-banner-border)');
    expect(tokens.colors.dangerBannerText).toBe('var(--color-danger-banner-text)');
  });

  // AC-5: New danger variants for clear-history error message
  // (chat-clear-history-error-message: dangerMessageBg/dangerMessageBorder/dangerMessageText)
  // Updated to CSS custom property references (Saga #360)
  it('exports dangerMessageBg, dangerMessageBorder, dangerMessageText as CSS custom property references (AC-5, clear-history-error-message, Saga #360)', () => {
    expect(tokens.colors.dangerMessageBg).toBe('var(--color-danger-message-bg)');
    expect(tokens.colors.dangerMessageBorder).toBe('var(--color-danger-message-border)');
    expect(tokens.colors.dangerMessageText).toBe('var(--color-danger-message-text)');
  });

  // AC-5: New success color variants for clear-history success message
  // (chat-clear-history-success-message: successBg/successBorder/successText)
  // Updated to CSS custom property references (Saga #360)
  it('exports successBg, successBorder, successText as CSS custom property references (AC-5, clear-history-success-message, Saga #360)', () => {
    expect(tokens.colors.successBg).toBe('var(--color-success-bg)');
    expect(tokens.colors.successBorder).toBe('var(--color-success-border)');
    expect(tokens.colors.successText).toBe('var(--color-success-text)');
  });

  // AC-4: New connected status color token for TransactionHistoryPanel
  // Updated to CSS custom property reference (Saga #360)
  it('exports connected color as CSS custom property reference (AC-4, connection-status, Saga #360)', () => {
    expect(tokens.colors.connected).toBe('var(--color-connected)');
  });

  it('exports white color as CSS custom property reference (AC-1, ChatScreen ham hex temizliği, Saga #360)', () => {
    expect(tokens.colors.white).toBe('var(--color-white)');
  });
});
