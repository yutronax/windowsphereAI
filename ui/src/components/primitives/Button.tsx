import { ReactNode, useState } from 'react';
import { tokens } from '../../tokens';

type Variant = 'primary' | 'danger';

interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'style'> {
  variant?: Variant;
  children: ReactNode;
  'data-testid'?: string;
}

const DISABLED_COLOR = '#94A3B8';

export default function Button({
  variant = 'primary',
  disabled = false,
  children,
  'data-testid': dataTestId,
  onMouseEnter,
  onMouseLeave,
  onMouseDown,
  onMouseUp,
  ...props
}: ButtonProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isActive, setIsActive] = useState(false);

  const getBackgroundColor = () => {
    if (disabled) {
      return DISABLED_COLOR;
    }

    if (variant === 'primary') {
      if (isActive) {
        return tokens.colors.primaryActive;
      }
      if (isHovered) {
        return tokens.colors.primaryHover;
      }
      return tokens.colors.primary;
    }

    // danger variant: statik renk, hover/active desteği yok
    return tokens.colors.danger;
  };

  const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    setIsHovered(true);
    onMouseEnter?.(e);
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    setIsHovered(false);
    setIsActive(false);
    onMouseLeave?.(e);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!disabled) {
      setIsActive(true);
    }
    onMouseDown?.(e);
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLButtonElement>) => {
    setIsActive(false);
    onMouseUp?.(e);
  };

  return (
    <button
      style={{
        backgroundColor: getBackgroundColor(),
        color: '#FFFFFF',
        height: tokens.size.buttonHeight,
        borderRadius: tokens.radius.default,
        padding: tokens.spacing.buttonPadding,
        fontSize: tokens.fontSize.base,
      }}
      disabled={disabled}
      data-testid={dataTestId}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      {...props}
    >
      {children}
    </button>
  );
}
