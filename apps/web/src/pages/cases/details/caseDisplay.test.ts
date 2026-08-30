import { describe, expect, it } from 'vitest';
import { displayCaseNumber, formatCaseDate } from './caseDisplay';

describe('case details display formatting', () => {
  it('shows the numeric case identifier without the legacy CASE prefix', () => {
    expect(displayCaseNumber('CASE-000021')).toBe('000021');
    expect(displayCaseNumber('000021')).toBe('000021');
  });

  it('uses a safe fallback for a missing date', () => {
    expect(formatCaseDate()).toBe('לא זמין');
  });
});
