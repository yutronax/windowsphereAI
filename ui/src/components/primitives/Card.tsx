import { ReactNode } from 'react';
import { tokens } from '../../tokens';

interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style'> {
  children?: ReactNode;
  'data-testid'?: string;
}

export default function Card({
  children,
  'data-testid': dataTestId,
  ...props
}: CardProps) {
  return (
    <div
      style={{
        backgroundColor: tokens.colors.panelBackground,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: tokens.radius.default,
      }}
      data-testid={dataTestId}
      {...props}
    >
      {children}
    </div>
  );
}
