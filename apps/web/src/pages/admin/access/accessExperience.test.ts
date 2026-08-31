import { describe, expect, it } from 'vitest';
import pageSource from './AccessPage.tsx?raw';
import cardsSource from './PermissionCards.tsx?raw';

describe('permission management experience', () => {
  it('loads the direct and effective matrix for a selected user or group', () => {
    expect(pageSource).toContain('/access/subjects/');
    expect(pageSource).toContain('/access/assignments');
    expect(cardsSource).toContain('effective_level');
  });
  it('persists bulk overrides and visually protects Admin defaults', () => {
    expect(pageSource).toContain("'/access/bulk'");
    expect(pageSource).toContain('Boolean(isAdmin)');
    expect(cardsSource).toContain('can_override===false');
    expect(pageSource).toContain("domain.scope==='environment'||domain.scope==='both'");
    expect(pageSource).toContain("text:'השינויים נשמרו בהצלחה'");
    expect(pageSource).toContain("text:'שמירת ההרשאות נכשלה'");
    expect(pageSource).toContain('/access/assignments?subject_type=');
  });
});
