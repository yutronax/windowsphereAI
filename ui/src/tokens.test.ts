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
});
