import { describe, expect, it } from 'vitest';
import source from './CaseDetailsPage.tsx?raw';

describe('case details semantic field architecture', () => {
  it('does not expose the legacy workflow status editor beside request type', () => {
    expect(source).not.toContain('/status-options');
    expect(source).not.toContain('StatusCascadeDialog');
    expect(source).not.toContain('<InputLabel>סטטוס</InputLabel>');
  });

  it('renders the configurable global fields as the active editing surface', () => {
    expect(source).toContain('fields={caseFields.global_fields}');
    expect(source).toContain('<GlobalFieldsPanel');
  });

  it('uses server permissions for lock overrides instead of blocking every locked case', () => {
    expect(source).toContain('const editable = Boolean(item?.permissions.can_edit)');
    expect(source).not.toContain('permissions.can_edit && !item?.is_locked');
  });
});
