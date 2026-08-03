import { describe, expect, it } from 'vitest';
import { parseCaseFieldOptions } from './caseFieldOptions';

describe('case field option editor', () => {
  it('normalizes comma-separated values and removes duplicates', () => {
    expect(parseCaseFieldOptions('SAP, Salesforce, SAP, Microsoft 365').map((item) => item.label_he))
      .toEqual(['SAP', 'Salesforce', 'Microsoft 365']);
  });

  it('stores structured values with a stable order', () => {
    expect(parseCaseFieldOptions('SAP, Microsoft 365')).toEqual([
      { value: 'sap', label_he: 'SAP', label_en: '', is_active: true, sort_order: 1 },
      { value: 'microsoft_365', label_he: 'Microsoft 365', label_en: '', is_active: true, sort_order: 2 },
    ]);
  });
});
