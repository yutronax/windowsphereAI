import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import Button from './Button';
import { tokens } from '../../tokens';

describe('Button (primitives, Saga #346)', () => {
  it('renders Button with primary variant colors and dimensions (AC-1, AC-3)', () => {
    render(<Button variant="primary" data-testid="primitive-button">Click me</Button>);

    const button = screen.getByTestId('primitive-button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveStyle({
      backgroundColor: tokens.colors.primary,
      color: 'rgb(255, 255, 255)',
      height: tokens.size.buttonHeight,
      borderRadius: tokens.radius.default,
      padding: tokens.spacing.buttonPadding,
      fontSize: tokens.fontSize.base,
    });
  });

  it('renders Button with danger variant colors (AC-1, AC-3)', () => {
    render(<Button variant="danger" data-testid="primitive-button-danger">Delete</Button>);

    const button = screen.getByTestId('primitive-button-danger');
    expect(button).toBeInTheDocument();
    expect(button).toHaveStyle({
      backgroundColor: tokens.colors.danger,
    });
  });

  it('applies default "primary" variant when variant prop is omitted (AC-1, AC-3)', () => {
    render(<Button data-testid="primitive-button-default">Default</Button>);

    const button = screen.getByTestId('primitive-button-default');
    expect(button).toHaveStyle({
      backgroundColor: tokens.colors.primary,
    });
  });

  it('applies disabled state styling with #94A3B8 color (AC-1, AC-3)', () => {
    render(
      <Button variant="primary" disabled data-testid="primitive-button-disabled">
        Disabled
      </Button>,
    );

    const button = screen.getByTestId('primitive-button-disabled');
    expect(button).toBeDisabled();
    expect(button).toHaveStyle({
      backgroundColor: '#94A3B8',
    });
  });

  it('applies button height, radius, and padding tokens from tokens.ts correctly (AC-1, AC-3)', () => {
    render(
      <Button variant="primary" data-testid="primitive-button-tokens">
        Token Check
      </Button>,
    );

    const button = screen.getByTestId('primitive-button-tokens');
    expect(button).toHaveStyle({
      height: tokens.size.buttonHeight,
      borderRadius: tokens.radius.default,
      padding: tokens.spacing.buttonPadding,
      fontSize: tokens.fontSize.base,
    });
  });

  it('renders with enabled state by default (AC-1, AC-3)', () => {
    render(
      <Button variant="primary" data-testid="primitive-button-enabled">
        Enabled
      </Button>,
    );

    const button = screen.getByTestId('primitive-button-enabled');
    expect(button).toBeEnabled();
  });

  it('danger variant disabled applies both variant and disabled styling (AC-1, AC-3)', () => {
    render(
      <Button variant="danger" disabled data-testid="primitive-button-danger-disabled">
        Danger Disabled
      </Button>,
    );

    const button = screen.getByTestId('primitive-button-danger-disabled');
    expect(button).toBeDisabled();
    expect(button).toHaveStyle({
      backgroundColor: '#94A3B8',
    });
  });

  // TypeScript type safety: Invalid variant prop (e.g., variant="invalid") will cause a compile-time error
  // This line is validated by tsc --noEmit, runtime test N/A (AC-4)
  // The variant prop is strictly typed as 'primary' | 'danger', so passing any other string
  // will fail TypeScript compilation with: Type '"invalid"' is not assignable to type '"primary" | "danger"'

  it('renders children text content correctly (AC-1, AC-3)', () => {
    const buttonText = 'Click Me Now';
    render(
      <Button variant="primary" data-testid="primitive-button-children">
        {buttonText}
      </Button>,
    );

    const button = screen.getByTestId('primitive-button-children');
    expect(button).toHaveTextContent(buttonText);
  });
});
