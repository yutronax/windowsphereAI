import { describe, expect, it } from 'vitest';

import { validatePlanResponse } from './planValidation';

describe('validatePlanResponse (plan-skeleton-sinir-sema-dogrulamasi / Saga #280)', () => {
  it('accepts a valid, complete plan (AC-1)', () => {
    const result = validatePlanResponse({
      steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'C:/Belgeler', affectedFileCount: 3 }],
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.plan.steps).toHaveLength(1);
      expect(result.plan.steps[0]).toEqual({ order: 1, operationType: 'Taşı', targetFolder: 'C:/Belgeler', affectedFileCount: 3 });
    }
  });

  it('accepts an empty steps array (AC-7, behaviour contract)', () => {
    const result = validatePlanResponse({ steps: [] });

    expect(result).toEqual({ ok: true, plan: { steps: [] } });
  });

  it('accepts optional securityStatus and rejectionReason when valid (AC-6)', () => {
    const result = validatePlanResponse({
      steps: [{ order: 0, operationType: 'Sil', targetFolder: 'X', affectedFileCount: 0 }],
      securityStatus: 'rejected',
      rejectionReason: 'Sandbox dışına çıkan yol.',
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.plan.securityStatus).toBe('rejected');
      expect(result.plan.rejectionReason).toBe('Sandbox dışına çıkan yol.');
    }
  });

  it('rejects a negative order (AC-2)', () => {
    const result = validatePlanResponse({ steps: [{ order: -1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 1 }] });

    expect(result.ok).toBe(false);
  });

  it('rejects a non-integer order (AC-2)', () => {
    const result = validatePlanResponse({ steps: [{ order: 1.5, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 1 }] });

    expect(result.ok).toBe(false);
  });

  it('rejects duplicate order values across steps (AC-2)', () => {
    const result = validatePlanResponse({
      steps: [
        { order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 1 },
        { order: 1, operationType: 'Sil', targetFolder: 'Y', affectedFileCount: 2 },
      ],
    });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/tekil/);
  });

  it('rejects an unknown operationType (AC-3)', () => {
    const result = validatePlanResponse({ steps: [{ order: 1, operationType: 'FormatDisk', targetFolder: 'X', affectedFileCount: 1 }] });

    expect(result.ok).toBe(false);
  });

  it('rejects a negative affectedFileCount (AC-4)', () => {
    const result = validatePlanResponse({ steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: -3 }] });

    expect(result.ok).toBe(false);
  });

  it('rejects an empty targetFolder (AC-5)', () => {
    const result = validatePlanResponse({ steps: [{ order: 1, operationType: 'Taşı', targetFolder: '  ', affectedFileCount: 1 }] });

    expect(result.ok).toBe(false);
  });

  it('rejects a non-object payload (AC-1, fail-closed)', () => {
    expect(validatePlanResponse(null).ok).toBe(false);
    expect(validatePlanResponse('plan').ok).toBe(false);
    expect(validatePlanResponse(42).ok).toBe(false);
  });

  it('rejects a payload without a steps array (AC-1, fail-closed)', () => {
    const result = validatePlanResponse({ steps: 'not-an-array' });

    expect(result.ok).toBe(false);
  });

  it('rejects an invalid securityStatus value (AC-6)', () => {
    const result = validatePlanResponse({ steps: [], securityStatus: 'maybe' });

    expect(result.ok).toBe(false);
  });

  it('rejects a non-string rejectionReason (AC-6)', () => {
    const result = validatePlanResponse({ steps: [], securityStatus: 'rejected', rejectionReason: 123 });

    expect(result.ok).toBe(false);
  });

  it('includes an actionable error message identifying the offending field (AC-8)', () => {
    const result = validatePlanResponse({ steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: -1 }] });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/affectedFileCount/);
  });
});
