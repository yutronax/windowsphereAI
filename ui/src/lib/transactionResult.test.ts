import { describe, expect, it } from 'vitest';

import { toTransactionResult } from './transactionResult';

describe('toTransactionResult (Saga #277)', () => {
  it('maps a committed transaction to completed, with deduplicated parent folders', () => {
    const result = toTransactionResult({
      status: 'committed',
      operations: [
        { destination_path: 'C:\\Users\\Yusuf\\Documents\\2026-08\\a.pdf', status: 'completed' },
        { destination_path: 'C:\\Users\\Yusuf\\Documents\\2026-08\\b.pdf', status: 'completed' },
        { destination_path: 'C:\\Users\\Yusuf\\Documents\\2026-09\\c.pdf', status: 'completed' },
      ],
    });

    expect(result.status).toBe('completed');
    expect(result.fileCount).toBe(3);
    expect(result.destinationFolders).toEqual(['C:/Users/Yusuf/Documents/2026-08', 'C:/Users/Yusuf/Documents/2026-09']);
  });

  it('maps a rolled_back transaction to failed with zero net file count (atomic all-or-nothing)', () => {
    const result = toTransactionResult({
      status: 'rolled_back',
      operations: [
        { destination_path: 'C:\\Users\\Yusuf\\Documents\\2026-08\\a.pdf', status: 'rolled_back' },
        { destination_path: 'C:\\Users\\Yusuf\\Documents\\2026-08\\b.pdf', status: 'rollback_failed' },
      ],
    });

    expect(result.status).toBe('failed');
    expect(result.fileCount).toBe(0);
    expect(result.destinationFolders).toEqual([]);
  });

  it('maps a pending transaction to partial, counting only the operations that actually completed', () => {
    const result = toTransactionResult({
      status: 'pending',
      operations: [
        { destination_path: 'C:\\Users\\Yusuf\\Documents\\2026-08\\a.pdf', status: 'completed' },
        { destination_path: 'C:\\Users\\Yusuf\\Documents\\2026-08\\b.pdf', status: 'pending' },
      ],
    });

    expect(result.status).toBe('partial');
    expect(result.fileCount).toBe(1);
    expect(result.destinationFolders).toEqual(['C:/Users/Yusuf/Documents/2026-08']);
  });

  it('handles an empty operations list without crashing', () => {
    const result = toTransactionResult({ status: 'committed', operations: [] });

    expect(result.fileCount).toBe(0);
    expect(result.destinationFolders).toEqual([]);
  });
});
