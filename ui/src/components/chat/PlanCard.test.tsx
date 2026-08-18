import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import PlanCard, { type Plan } from './PlanCard';

const onePlan: Plan = { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 1 }] };

describe('PlanCard (plan-adimlari-kart / Saga #262)', () => {
  it('renders each step with order number, operation type, target folder and file count (AC-1, AC-2)', () => {
    const plan: Plan = {
      steps: [
        { order: 1, operationType: 'Taşı', targetFolder: 'C:/Belgeler/Arşiv', affectedFileCount: 3 },
        { order: 2, operationType: 'Sil', targetFolder: 'C:/Belgeler/Geçici', affectedFileCount: 12 },
      ],
    };
    render(<PlanCard plan={plan} />);

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('Taşı');
    expect(items[0]).toHaveTextContent('C:/Belgeler/Arşiv');
    expect(items[0]).toHaveTextContent('3 dosya');
    expect(items[1]).toHaveTextContent('Sil');
    expect(items[1]).toHaveTextContent('12 dosya');
  });

  it('renders steps in order regardless of input array order (AC-3)', () => {
    const plan: Plan = {
      steps: [
        { order: 2, operationType: 'Taşı', targetFolder: 'İkinci-klasör', affectedFileCount: 1 },
        { order: 1, operationType: 'Taşı', targetFolder: 'Birinci-klasör', affectedFileCount: 1 },
      ],
    };
    render(<PlanCard plan={plan} />);

    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('Birinci-klasör');
    expect(items[1]).toHaveTextContent('İkinci-klasör');
  });

  it('uses an ordered list structure for accessible step-order announcement (AC-4)', () => {
    render(<PlanCard plan={{ steps: [{ order: 1, operationType: 'Kopyala', targetFolder: 'X', affectedFileCount: 1 }] }} />);

    expect(screen.getByRole('list').tagName).toBe('OL');
  });

  it('renders an empty step list without error (behaviour contract)', () => {
    render(<PlanCard plan={{ steps: [] }} />);

    expect(screen.getByTestId('plan-card')).toBeVisible();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });

  it('shows "0 dosya" instead of hiding a zero affected-file-count step (behaviour contract)', () => {
    render(<PlanCard plan={{ steps: [{ order: 1, operationType: 'Listele', targetFolder: 'X', affectedFileCount: 0 }] }} />);

    expect(screen.getByText(/0 dosya/)).toBeVisible();
  });

  it('fails closed: disables the approve button and shows a pending message when securityStatus is absent (Saga #263 AC-1/AC-2, red-team fix)', () => {
    const onApprove = vi.fn();
    render(<PlanCard plan={onePlan} onApprove={onApprove} />);

    const button = screen.getByTestId('plan-approve-button');
    expect(button).toBeDisabled();
    expect(screen.getByTestId('plan-pending-status')).toHaveTextContent('Güvenlik kontrolü bekleniyor');
    fireEvent.click(button);
    expect(onApprove).not.toHaveBeenCalled();
  });

  it('enables the approve button ONLY when securityStatus is "approved", and calls onApprove when clicked (Saga #263 AC-4, AC-6)', () => {
    const onApprove = vi.fn();
    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} onApprove={onApprove} />);

    const button = screen.getByTestId('plan-approve-button');
    expect(button).toBeEnabled();
    expect(screen.queryByTestId('plan-rejection-reason')).not.toBeInTheDocument();
    expect(screen.queryByTestId('plan-pending-status')).not.toBeInTheDocument();
    fireEvent.click(button);
    expect(onApprove).toHaveBeenCalledOnce();
  });

  it('disables the approve button and shows the rejection reason when securityStatus is "rejected" (Saga #263 AC-3)', () => {
    render(<PlanCard plan={{ ...onePlan, securityStatus: 'rejected', rejectionReason: 'Sandbox dışına çıkan yol tespit edildi.' }} />);

    expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
    expect(screen.getByTestId('plan-rejection-reason')).toHaveTextContent('Sandbox dışına çıkan yol tespit edildi.');
  });

  it('shows a default rejection message when rejected without an explicit reason (behaviour contract)', () => {
    render(<PlanCard plan={{ ...onePlan, securityStatus: 'rejected' }} />);

    expect(screen.getByTestId('plan-rejection-reason')).toHaveTextContent('Bu plan güvenlik kontrolünden geçemedi.');
  });

  it('ignores a rapid second click after approval (double-submit guard, red-team fix)', () => {
    const onApprove = vi.fn();
    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} onApprove={onApprove} />);

    const button = screen.getByTestId('plan-approve-button');
    fireEvent.click(button);
    fireEvent.click(button);
    expect(onApprove).toHaveBeenCalledOnce();
  });

  it('links the disabled state to its status text via aria-describedby (screen reader, red-team fix)', () => {
    render(<PlanCard plan={{ ...onePlan, securityStatus: 'rejected', rejectionReason: 'Yetkisiz dizin.' }} />);

    const button = screen.getByTestId('plan-approve-button');
    const describedById = button.getAttribute('aria-describedby');
    expect(describedById).toBeTruthy();
    expect(document.getElementById(describedById!)).toHaveTextContent('Yetkisiz dizin.');
  });

  it('gives the approve button a 44px minimum touch target (Saga #263 AC-5)', () => {
    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} />);

    expect(screen.getByTestId('plan-approve-button')).toHaveClass('plan-card-approve-btn');
  });

  it('calls onChangePlan and NOT onApprove when "Planı değiştir" is clicked (Saga #264 AC-1)', () => {
    const onApprove = vi.fn();
    const onChangePlan = vi.fn();
    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} onApprove={onApprove} onChangePlan={onChangePlan} />);

    fireEvent.click(screen.getByTestId('plan-change-button'));

    expect(onChangePlan).toHaveBeenCalledOnce();
    expect(onApprove).not.toHaveBeenCalled();
  });

  it('disables both approve and change-plan buttons while a new plan is generating (Saga #265 red-team fix)', () => {
    const onApprove = vi.fn();
    const onChangePlan = vi.fn();
    render(
      <PlanCard
        plan={{ ...onePlan, securityStatus: 'approved' }}
        onApprove={onApprove}
        onChangePlan={onChangePlan}
        isGeneratingPlan
      />,
    );

    expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
    expect(screen.getByTestId('plan-change-button')).toBeDisabled();
  });

  it('permanently disables approval and shows a stale message when stale=true (Saga #264 AC-4)', () => {
    const onApprove = vi.fn();
    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} onApprove={onApprove} stale />);

    const button = screen.getByTestId('plan-approve-button');
    expect(button).toBeDisabled();
    expect(screen.getByTestId('plan-stale-status')).toHaveTextContent('Bu plan artık geçerli değil, yeni plan bekleniyor.');
    fireEvent.click(button);
    expect(onApprove).not.toHaveBeenCalled();
  });

  it('approves in a single click when total affectedFileCount is at or below the bulk-confirm threshold (Saga #311, AC-1)', () => {
    const onApprove = vi.fn();
    const plan: Plan = {
      steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 20 }],
      securityStatus: 'approved',
    };
    render(<PlanCard plan={plan} onApprove={onApprove} />);

    fireEvent.click(screen.getByTestId('plan-approve-button'));
    expect(onApprove).toHaveBeenCalledOnce();
    expect(screen.queryByTestId('plan-bulk-confirm-button')).not.toBeInTheDocument();
  });

  it('requires a second explicit confirmation when total affectedFileCount exceeds the bulk-confirm threshold (Saga #311, AC-2)', () => {
    const onApprove = vi.fn();
    const plan: Plan = {
      steps: [
        { order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 15 },
        { order: 2, operationType: 'Sil', targetFolder: 'Y', affectedFileCount: 6 },
      ],
      securityStatus: 'approved',
    };
    render(<PlanCard plan={plan} onApprove={onApprove} />);

    fireEvent.click(screen.getByTestId('plan-approve-button'));
    expect(onApprove).not.toHaveBeenCalled();
    expect(screen.getByTestId('plan-bulk-confirm-button')).toBeVisible();
    expect(screen.getByTestId('plan-bulk-confirm-button')).toHaveTextContent('21');
  });

  it('calls onApprove only after the second bulk-confirm click, and cancel does not call onApprove (Saga #311, AC-3)', () => {
    const onApprove = vi.fn();
    const plan: Plan = {
      steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 25 }],
      securityStatus: 'approved',
    };
    render(<PlanCard plan={plan} onApprove={onApprove} />);

    fireEvent.click(screen.getByTestId('plan-approve-button'));
    fireEvent.click(screen.getByTestId('plan-bulk-confirm-cancel-button'));
    expect(onApprove).not.toHaveBeenCalled();
    expect(screen.getByTestId('plan-approve-button')).toBeVisible();

    fireEvent.click(screen.getByTestId('plan-approve-button'));
    fireEvent.click(screen.getByTestId('plan-bulk-confirm-button'));
    expect(onApprove).toHaveBeenCalledOnce();
  });
});
