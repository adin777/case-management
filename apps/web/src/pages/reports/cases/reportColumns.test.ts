import { describe, expect, it } from 'vitest';
import { reportColumns } from './reportColumns';

describe('case report columns', () => {
  it('exposes the required core columns with Hebrew labels', () => {
    expect(reportColumns).toContainEqual(['case_number', 'מספר קריאה']);
    expect(reportColumns).toContainEqual(['description', 'תיאור']);
    expect(reportColumns).toContainEqual(['updated_at', 'עודכן']);
  });

  it('does not expose duplicate column keys', () => {
    const keys = reportColumns.map(([key]) => key);
    expect(new Set(keys).size).toBe(keys.length);
  });
});
