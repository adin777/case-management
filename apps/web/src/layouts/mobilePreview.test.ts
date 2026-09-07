import { describe, expect, it } from 'vitest';
import layout from './AppLayout.tsx?raw';
import preview from './MobilePreviewDialog.tsx?raw';
import routes from '../App.tsx?raw';

describe('authorized mobile preview and implementer routes', () => {
  it('uses a real responsive iframe viewport only for system admins', () => {
    expect(layout).toContain('user?.is_system_admin&&!embeddedPreview');
    expect(preview).toContain('component="iframe"');
    expect(preview).toContain('[375, 390, 430]');
    expect(preview).not.toMatch(/transform|scale\(/);
  });

  it('guards implementer and direct configuration routes in the frontend', () => {
    expect(routes.match(/<CapabilityGuard>/g)?.length).toBeGreaterThanOrEqual(7);
    expect(routes).toContain('path="/implementer"');
  });
});
