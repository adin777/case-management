import { describe, expect, it } from 'vitest';
import { normalizeTransferRequirements } from './CaseTransferWizard';

describe('normalizeTransferRequirements', () => {
  it('provides safe empty lists for a malformed API response', () => {
    expect(normalizeTransferRequirements({ priorities: null, required_fields: 'invalid' })).toEqual({
      initial_status_label: '', required_fields: [], removed_fields: [], field_mappings: [],
      priorities: [], sub_priorities: [], assignees: [],
    });
  });
});
