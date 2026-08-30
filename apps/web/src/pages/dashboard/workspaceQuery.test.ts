import { describe, expect, it } from 'vitest';
import { buildWorkspaceQuery, nextWorkspaceSort } from './workspaceQuery';
import type { WorkspaceFilters } from './types';

const filters: WorkspaceFilters = { activity_state: 'all', search: '000021', created_from: '', created_to: '', title: 'תקלה', updated_from: '', updated_to: '', environment_id: 'env-1', include_participating: true, dynamic: {} };
describe('workspace backend query', () => {
  it('sends search, filters, visibility, paging and sorting to the backend', () => {
    const query = new URLSearchParams(buildWorkspaceQuery(filters, 'my', 2, 50, 'case_number:asc'));
    expect(Object.fromEntries(query)).toMatchObject({ search: '000021', title: 'תקלה', environment_id: 'env-1', include_participating: 'true', page: '2', page_size: '50', sort: 'case_number:asc' });
  });
  it('toggles sorting deterministically', () => {
    expect(nextWorkspaceSort('title:asc', 'title')).toBe('title:desc');
    expect(nextWorkspaceSort('updated_at:desc', 'title')).toBe('title:asc');
  });
});
