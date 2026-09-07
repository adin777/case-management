import { describe, expect, it } from 'vitest';
import portal from './PortalHomePage.tsx?raw';
import routes from '../../App.tsx?raw';
import layout from '../../layouts/AppLayout.tsx?raw';

describe('portal and capability based workspace experience', () => {
  it('has a distinct portal backed by the visible-case workspace API', () => {
    expect(portal).toContain("'/cases/workspace/query?");
    expect(portal).toContain('פתיחת קריאה חדשה');
    expect(portal).toContain('קריאות אחרונות');
    expect(routes).toContain('path="/portal"');
    expect(routes).toContain('path="/workspace"');
  });

  it('shows the agent workspace from a server-provided capability', () => {
    expect(layout).toContain('user?.can_use_agent_workspace');
    expect(layout).not.toMatch(/role\s*===|role_name/);
  });
});
