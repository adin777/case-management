import { describe, expect, it } from 'vitest';
import pageSource from '../GlobalFieldsPage.tsx?raw';
import optionsSource from './GlobalOptionsDialog.tsx?raw';

describe('global fields administration experience', () => {
  it('keeps CRUD, safe activation and database-backed option management connected', () => {
    expect(pageSource).toContain("'/global-case-fields?include_inactive=true'");
    expect(pageSource).toContain("method:'DELETE'");
    expect(pageSource).toContain('<GlobalOptionsDialog');
    expect(pageSource).toContain('ניהול ערכים ({row.options.length})');
    expect(optionsSource).toContain('שם בעברית');
    expect(optionsSource).toContain('תרגום באנגלית');
    expect(optionsSource).toContain("'aria-label':'פעיל'");
  });
  it('uses drag and drop endpoints instead of manual order inputs', () => {
    expect(pageSource).toContain("'/global-case-fields/order'");
    expect(pageSource).toContain('/options/order');
    expect(optionsSource).toContain('onReorder(next.map');
    expect(optionsSource).toContain('DragIndicator');
    expect(optionsSource).not.toContain('label="סדר"');
  });
});
