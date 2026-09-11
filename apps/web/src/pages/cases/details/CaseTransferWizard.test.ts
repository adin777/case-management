import { describe, expect, it } from 'vitest';
import { normalizeTransferRequirements } from './CaseTransferWizard';

describe('normalizeTransferRequirements', () => {
  it('provides safe empty lists for a malformed API response', () => {
    expect(normalizeTransferRequirements({ required_fields: 'invalid' })).toEqual({
      required_fields: [], removed_fields: [], field_mappings: [], assignees: [],
    });
  });
});
