import { ReactNode, useState } from 'react';
import { tokens } from '../../tokens';

type Variant = 'primary' | 'danger' | 'danger-outline' | 'secondary';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
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
  style: propStyle,
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

    if (variant === 'danger-outline' || variant === 'secondary') {
      return tokens.colors.white;
    }

    // danger variant: statik renk, hover/active desteği yok
    return tokens.colors.danger;
  };

  const getTextColor = () => {
    if (disabled) {
      return '#FFFFFF';
    }

    if (variant === 'danger-outline') {
      return tokens.colors.danger;
    }

    if (variant === 'secondary') {
      return tokens.colors.textDark;
    }

    return '#FFFFFF';
  };

  const getBorderStyle = () => {
    if (disabled) {
      return 'none';
    }

    if (variant === 'danger-outline') {
      return `1px solid ${tokens.colors.danger}`;
    }

    if (variant === 'secondary') {
      return `1px solid ${tokens.colors.border}`;
    }

    return 'none';
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
        color: getTextColor(),
        border: getBorderStyle(),
        height: tokens.size.buttonHeight,
        borderRadius: tokens.radius.default,
        padding: tokens.spacing.buttonPadding,
        fontSize: tokens.fontSize.base,
        ...propStyle,
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
