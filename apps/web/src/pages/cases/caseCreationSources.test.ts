import { describe, expect, it } from 'vitest';
import { activeRequestTypes, requestTypesUrl } from './caseCreationSources';
import type { RequestType } from '../../types';

describe('case creation sources', () => {
  it('requests active request types for the selected environment', () => {
    expect(requestTypesUrl('environment-a')).toBe(
      '/request-types?environment_id=environment-a&active_only=true',
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
