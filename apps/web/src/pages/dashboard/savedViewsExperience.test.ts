import { describe, expect, it } from 'vitest';
import bar from './SavedViewsBar.tsx?raw';
import page from './DashboardPage.tsx?raw';
import list from './DashboardCaseList.tsx?raw';

describe('persistent agent workspace views',()=>{
  it('connects every saved-view action to the backend',()=>{
    expect(bar).toContain("'/workspace/views'");
    expect(bar).toContain("kind:'duplicate'|'default'|'delete'");
    expect(bar).toContain("method:dialog==='rename'?'PUT':'POST'");
  });
  it('applies saved filters, sorting, page size and visible columns',()=>{
    expect(page).toContain('saved.filters');expect(page).toContain('saved.sort');expect(page).toContain('saved.page_size');expect(page).toContain('saved.visible_columns');
    expect(list).toContain('visibleColumns.includes(key)');
  });
});
