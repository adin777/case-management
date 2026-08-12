import { describe, expect, it } from 'vitest';
import { parseCaseFieldOptions } from './caseFieldOptions';

describe('case field option editor', () => {
  it('normalizes comma-separated values and removes duplicates', () => {
    expect(parseCaseFieldOptions('SAP, Salesforce, SAP, Microsoft 365').map((item) => item.label_he))
      .toEqual(['SAP', 'Salesforce', 'Microsoft 365']);
  });

  it('generates stable technical codes without asking the administrator for them', () => {
    const first=parseCaseFieldOptions('SAP, מערכת פנים');const second=parseCaseFieldOptions('SAP, מערכת פנים');
    expect(first).toEqual(second);expect(first.map(item=>item.sort_order)).toEqual([1,2]);
    expect(first.every(item=>/^option_\d+_[a-z0-9]+$/.test(item.value))).toBe(true);
  });
});
