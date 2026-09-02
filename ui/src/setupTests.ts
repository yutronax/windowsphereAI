import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from 'jest-extended';
import { afterEach, expect } from 'vitest';
import { tokens } from './tokens';
import './theme.css';

expect.extend(matchers);

// Saga #360: Setup localStorage mock for theme tests
// NOTE: jsdom's localStorage in this test environment is not a proper Storage instance
// and lacks methods like .clear(). Rather than augmenting the broken default, we replace
// it wholesale. Direct property mutation via Object.assign doesn't work on jsdom's Storage-like
// object, so this full-replacement approach is necessary. Tests relying on storage clearing
// (theme.test.ts, etc.) depend on this mock.
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
});

// Saga #360: CSS custom properties map for resolving var() in tests
// WARNING: This map must be manually kept in sync with the :root block in ui/src/theme.css.
// When color values in theme.css change, this map must be updated accordingly, otherwise
// tests using toHaveStyle() will validate against stale/incorrect values. Reason: jsdom's
// test environment does not resolve CSS var() functions like a real browser does, so test
// assertions require JS-side color values to be available for comparison.
const cssVariableMap: Record<string, string> = {
  '--color-primary': '#1E3A8A',
  '--color-primary-hover': '#1E3172',
  '--color-primary-active': '#172554',
  '--color-border': '#E5E7EB',
  '--color-danger': '#DC2626',
  '--color-text-secondary': '#4B5563',
  '--color-text-muted': '#6B7280',
  '--color-text-dark': '#111827',
  '--color-panel-background': '#F3F4F6',
  '--color-danger-banner-bg': '#FEF2F2',
  '--color-danger-banner-border': '#FCA5A5',
  '--color-danger-banner-text': '#B91C1C',
  '--color-danger-message-bg': '#FEE2E2',
  '--color-danger-message-border': '#FECACA',
  '--color-danger-message-text': '#991B1B',
  '--color-success-bg': '#D1FAE5',
  '--color-success-border': '#A7F3D0',
  '--color-success-text': '#065F46',
  '--color-connected': '#059669',
  '--color-white': '#fff',
};

function hexToRgb(hex: string): string {
  // Handle both 3-digit and 6-digit hex colors
  let cleanHex = hex.replace('#', '');
  if (cleanHex.length === 3) {
    cleanHex = cleanHex.split('').map((char) => char + char).join('');
  }
  const result = /^([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(cleanHex);
  if (result) {
    return `rgb(${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)})`;
  }
  return hex;
}

function resolveVarReferences(value: string): string {
  const resolved = value.replace(/var\((--[^)]+)\)/g, (match, varName) => cssVariableMap[varName] || value);
  // Convert hex colors to RGB format to match jsdom's normalization
  return resolved.replace(/#[a-f\d]{3}(?:[a-f\d]{3})?/gi, hexToRgb);
}

// Mock CSSStyleDeclaration's getPropertyValue to resolve custom properties
const originalGetPropertyValue = CSSStyleDeclaration.prototype.getPropertyValue;
CSSStyleDeclaration.prototype.getPropertyValue = function (prop: string) {
  const value = originalGetPropertyValue.call(this, prop);
  return resolveVarReferences(value);
};

// Value-based consistency check: ensure every token.colors.X references a CSS variable in cssVariableMap
function validateTokensConsistency() {
  for (const [key, value] of Object.entries(tokens.colors)) {
    const varMatch = value.match(/var\((--[^)]+)\)/);
    if (!varMatch) {
      throw new Error(
        `[setupTests.ts] Invalid token value for tokens.colors.${key}: "${value}" does not contain var(...)`
      );
    }
    const varName = varMatch[1];
    if (!cssVariableMap[varName]) {
      throw new Error(
        `[setupTests.ts] CSS variable ${varName} (referenced by tokens.colors.${key}) ` +
        `not found in cssVariableMap. Ensure both stay synchronized to prevent test flakiness.`
      );
    }
  }
}

validateTokensConsistency();

afterEach(() => {
  cleanup();
  localStorage.clear();
});
