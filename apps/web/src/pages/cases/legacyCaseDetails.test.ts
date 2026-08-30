import { describe, expect, it } from 'vitest';
import source from './CaseDetailsPage.tsx?raw';

describe('case details semantic field architecture', () => {
  it('does not expose the legacy workflow status editor beside request type', () => {
    expect(source).not.toContain('/status-options');
    expect(source).not.toContain('StatusCascadeDialog');
    expect(source).not.toContain('<InputLabel>סטטוס</InputLabel>');
  });

  it('renders the configurable global fields as the active editing surface', () => {
    expect(source).toContain('caseFields.global_fields.map');
    expect(source).toContain("field.semantic_binding==='case.assignee'");
  });
});
