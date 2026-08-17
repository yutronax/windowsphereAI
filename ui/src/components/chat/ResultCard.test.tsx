import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import ResultCard from './ResultCard';

describe('ResultCard (Saga #277)', () => {
  it('shows the processed file count (AC-2)', () => {
    render(<ResultCard result={{ fileCount: 3, destinationFolders: ['2026-08'], status: 'completed' }} />);

    expect(screen.getByTestId('result-file-count')).toHaveTextContent('3 dosya işlendi');
  });

  it('lists all destination folders (AC-2)', () => {
    render(
      <ResultCard result={{ fileCount: 3, destinationFolders: ['2026-07', '2026-08'], status: 'completed' }} />,
    );

    const list = screen.getByTestId('result-destination-folders');
    expect(list).toHaveTextContent('2026-07');
    expect(list).toHaveTextContent('2026-08');
  });

  it('shows a clear empty-state message when no folders were created, without crashing (AC-6)', () => {
    render(<ResultCard result={{ fileCount: 0, destinationFolders: [], status: 'completed' }} />);

    expect(screen.getByTestId('result-no-folders')).toHaveTextContent('Hiçbir klasör oluşturulmadı.');
    expect(screen.queryByTestId('result-destination-folders')).not.toBeInTheDocument();
  });

  it('shows a distinguishable completion status text (AC-3)', () => {
    render(<ResultCard result={{ fileCount: 1, destinationFolders: ['2026-08'], status: 'completed' }} />);

    expect(screen.getByTestId('result-status-text')).toHaveTextContent('İşlem tamamlandı.');
  });

  it('visually distinguishes a failed status from a completed one (AC-3)', () => {
    render(<ResultCard result={{ fileCount: 0, destinationFolders: [], status: 'failed' }} />);

    const statusText = screen.getByTestId('result-status-text');
    expect(statusText).toHaveTextContent('İşlem tamamlanamadı.');
    expect(statusText).toHaveClass('is-failed');
  });

  it('announces the status text inside an aria-live polite region (AC-4)', () => {
    render(<ResultCard result={{ fileCount: 1, destinationFolders: ['2026-08'], status: 'completed' }} />);

    const region = screen.getByTestId('result-status-text').closest('[aria-live]');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });
});
