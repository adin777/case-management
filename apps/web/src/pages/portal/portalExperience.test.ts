import { describe, expect, it } from 'vitest';
import portal from './PortalHomePage.tsx?raw';
import routes from '../../App.tsx?raw';
import layout from '../../layouts/AppLayout.tsx?raw';
import he from '../../i18n/locales/he.json';

describe('portal and capability based workspace experience', () => {
  it('has a distinct portal backed by the visible-case workspace API', () => {
    expect(portal).toContain("'/cases/workspace/query?");
    expect(portal).toContain("t('cases.createTitle')");
    expect(portal).toContain("t('portal.recent')");
    expect(he.cases.createTitle).toBe('פתיחת קריאה חדשה');
    expect(he.portal.recent).toBe('קריאות אחרונות');
    expect(routes).toContain('path="/portal"');
    expect(routes).toContain('path="/workspace"');
  });

  it('shows the agent workspace from a server-provided capability', () => {
    expect(layout).toContain('user?.can_use_agent_workspace');
    expect(layout).not.toMatch(/role\s*===|role_name/);
  });
});
