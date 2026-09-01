import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import Card from './Card';
import { tokens } from '../../tokens';

describe('Card (primitives, Saga #346)', () => {
  it('renders Card with panel background, border, and radius tokens (AC-2, AC-3)', () => {
    render(
      <Card data-testid="primitive-card">
        <p>Card content</p>
      </Card>,
    );

    const card = screen.getByTestId('primitive-card');
    expect(card).toBeInTheDocument();
    expect(card).toHaveStyle({
      backgroundColor: tokens.colors.panelBackground,
      border: `1px solid ${tokens.colors.border}`,
      borderRadius: tokens.radius.default,
    });
  });

  it('renders children content inside the Card (AC-2, AC-3)', () => {
    const childText = 'This is card content';
    render(
      <Card data-testid="primitive-card-children">
        <p>{childText}</p>
      </Card>,
    );

    const card = screen.getByTestId('primitive-card-children');
    expect(card).toHaveTextContent(childText);
    expect(screen.getByText(childText)).toBeInTheDocument();
  });

  it('applies panelBackground token value from tokens.ts correctly (AC-2, AC-3)', () => {
    render(
      <Card data-testid="primitive-card-bg">
        Content
      </Card>,
    );

    const card = screen.getByTestId('primitive-card-bg');
    expect(card).toHaveStyle({
      backgroundColor: tokens.colors.panelBackground,
    });
  });

  it('applies border token value from tokens.ts correctly (AC-2, AC-3)', () => {
    render(
      <Card data-testid="primitive-card-border">
        Bordered content
      </Card>,
    );

    const card = screen.getByTestId('primitive-card-border');
    expect(card).toHaveStyle({
      border: `1px solid ${tokens.colors.border}`,
    });
  });

  it('applies radius token value from tokens.ts correctly (AC-2, AC-3)', () => {
    render(
      <Card data-testid="primitive-card-radius">
        Rounded content
      </Card>,
    );

    const card = screen.getByTestId('primitive-card-radius');
    expect(card).toHaveStyle({
      borderRadius: tokens.radius.default,
    });
  });

  it('renders multiple children elements correctly (AC-2, AC-3)', () => {
    render(
      <Card data-testid="primitive-card-multiple-children">
        <h2>Card Title</h2>
        <p>Card description</p>
        <button>Action</button>
      </Card>,
    );

    const card = screen.getByTestId('primitive-card-multiple-children');
    expect(screen.getByText('Card Title')).toBeInTheDocument();
    expect(screen.getByText('Card description')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
  });

  it('renders empty Card without error (behaviour contract, AC-2, AC-3)', () => {
    render(<Card data-testid="primitive-card-empty" />);

    const card = screen.getByTestId('primitive-card-empty');
    expect(card).toBeInTheDocument();
    expect(card).toHaveStyle({
      backgroundColor: tokens.colors.panelBackground,
      border: `1px solid ${tokens.colors.border}`,
      borderRadius: tokens.radius.default,
    });
  });

  it('applies all token values together in a single Card instance (AC-2, AC-3)', () => {
    render(
      <Card data-testid="primitive-card-all-tokens">
        <div>All tokens applied</div>
      </Card>,
    );

    const card = screen.getByTestId('primitive-card-all-tokens');
    expect(card).toHaveStyle({
      backgroundColor: tokens.colors.panelBackground,
      border: `1px solid ${tokens.colors.border}`,
      borderRadius: tokens.radius.default,
    });
    expect(screen.getByText('All tokens applied')).toBeInTheDocument();
  });
});
