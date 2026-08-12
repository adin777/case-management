import { describe, expect, it } from 'vitest';
import { activeRequestTypes, caseCreationConfigurationUrl } from './caseCreationSources';
import type { RequestType } from '../../types';

describe('case creation sources', () => {
  it('requests active request types for the selected environment', () => {
    expect(caseCreationConfigurationUrl('environment-a')).toBe(
      '/case-creation/environments/environment-a/configuration',
    );
  });

  it('never renders environments, inactive rows, or rows from another environment as request types', () => {
    const rows = [
      { id: 'a1', environment_id: 'a', name_he: 'סוג א-1', is_active: true },
      { id: 'a2', environment_id: 'a', name_he: 'סוג א-2', is_active: true },
      { id: 'b1', environment_id: 'b', name_he: 'סוג ב-1', is_active: true },
      { id: 'inactive', environment_id: 'a', name_he: 'לא פעיל', is_active: false },
    ] as RequestType[];
    expect(activeRequestTypes(rows, 'a').map((row) => row.name_he)).toEqual(['סוג א-1', 'סוג א-2']);
  });
});
