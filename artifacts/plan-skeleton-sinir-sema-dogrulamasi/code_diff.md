import type { Plan, PlanStep } from './PlanCard';

export const KNOWN_OPERATION_TYPES = ['Taşı', 'Kopyala', 'Sil', 'Yeniden Adlandır', 'Listele'] as const;

export type PlanValidationResult = { ok: true; plan: Plan } | { ok: false; error: string };

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0;
}

function validateStep(raw: unknown, index: number): PlanStep | string {
  if (typeof raw !== 'object' || raw === null) {
    return `steps[${index}] bir obje değil`;
  }
  const step = raw as Record<string, unknown>;

  if (!isNonNegativeInteger(step.order)) {
    return `steps[${index}].order negatif olmayan bir tamsayı olmalı`;
  }
  if (typeof step.operationType !== 'string' || !(KNOWN_OPERATION_TYPES as readonly string[]).includes(step.operationType)) {
    return `steps[${index}].operationType bilinen bir işlem türü olmalı (${KNOWN_OPERATION_TYPES.join(', ')})`;
  }
  if (typeof step.targetFolder !== 'string' || step.targetFolder.trim() === '') {
    return `steps[${index}].targetFolder boş olmayan bir string olmalı`;
  }
  if (!isNonNegativeInteger(step.affectedFileCount)) {
    return `steps[${index}].affectedFileCount negatif olmayan bir tamsayı olmalı`;
  }

  return {
    order: step.order,
    operationType: step.operationType,
    targetFolder: step.targetFolder,
    affectedFileCount: step.affectedFileCount,
  };
}

export function validatePlanResponse(data: unknown): PlanValidationResult {
  if (typeof data !== 'object' || data === null) {
    return { ok: false, error: 'plan bir obje değil' };
  }
  const plan = data as Record<string, unknown>;

  if (!Array.isArray(plan.steps)) {
    return { ok: false, error: 'plan.steps bir dizi olmalı' };
  }

  const steps: PlanStep[] = [];
  const seenOrders = new Set<number>();
  for (let i = 0; i < plan.steps.length; i++) {
    const result = validateStep(plan.steps[i], i);
    if (typeof result === 'string') {
      return { ok: false, error: result };
    }
    if (seenOrders.has(result.order)) {
      return { ok: false, error: `steps[${i}].order (${result.order}) tekil olmalı, tekrar ediyor` };
    }
    seenOrders.add(result.order);
    steps.push(result);
  }

  if (plan.securityStatus !== undefined && plan.securityStatus !== 'approved' && plan.securityStatus !== 'rejected') {
    return { ok: false, error: 'plan.securityStatus "approved" veya "rejected" olmalı' };
  }
  if (plan.rejectionReason !== undefined && typeof plan.rejectionReason !== 'string') {
    return { ok: false, error: 'plan.rejectionReason bir string olmalı' };
  }

  return {
    ok: true,
    plan: {
      steps,
      ...(plan.securityStatus !== undefined ? { securityStatus: plan.securityStatus as 'approved' | 'rejected' } : {}),
      ...(plan.rejectionReason !== undefined ? { rejectionReason: plan.rejectionReason as string } : {}),
    },
  };
}
