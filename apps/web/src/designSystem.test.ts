import { describe, expect, it } from 'vitest';
import { getContrastRatio } from '@mui/material/styles';
import { createAppTheme, designTokens } from './theme';
import layout from './layouts/AppLayout.tsx?raw';
import { isNavigationActive } from './layouts/navigationState';

// These constraints protect the shared visual contract across all page consumers.
describe('shared application design', () => {
  it('keeps readable text and primary actions on all base surfaces', () => {
    for (const background of [designTokens.paper, designTokens.canvas, designTokens.navigation]) {
      expect(getContrastRatio(designTokens.text, background)).toBeGreaterThanOrEqual(4.5);
      expect(getContrastRatio(designTokens.muted, background)).toBeGreaterThanOrEqual(4.5);
    }
    expect(getContrastRatio(designTokens.paper, designTokens.ink)).toBeGreaterThanOrEqual(4.5);
  });
  it.each(['rtl', 'ltr'] as const)('applies the same tokens and reading direction in %s', direction => {
    const theme = createAppTheme(direction);
    expect(theme.direction).toBe(direction);
    expect(theme.palette.primary.main).toBe(designTokens.ink);
    expect(theme.typography.fontFamily).toContain('Noto Sans Hebrew');
    expect(theme.components?.MuiTableCell?.styleOverrides?.root).toMatchObject({ textAlign: direction === 'rtl' ? 'right' : 'left' });
    expect(theme.components?.MuiButton?.styleOverrides?.startIcon).toEqual({ margin: 0 });
  });
  it('respects reduced motion and avoids the old animated card lift', () => {
    const baseline = createAppTheme('rtl').components?.MuiCssBaseline?.styleOverrides;
    expect(baseline).toHaveProperty('@media (prefers-reduced-motion: reduce)');
  });
  it('keeps the main action reachable without covering case form/detail actions', () => {
    expect(layout).toContain("!routeLocation.pathname.startsWith('/cases/')");
    expect(layout).toContain('safe-area-inset-bottom');
    expect(layout).toContain('aria-current=');
  });
});

describe('navigation selection survives nested screens', () => {
  it.each([
    ['/reports/cases', '/reports'], ['/reports/audit', '/reports'],
    ['/admin/environments', '/implementer'], ['/admin/users', '/implementer'],
    ['/portal', '/'], ['/workspace', '/workspace'],
  ])('keeps %s in the %s section', (path, section) => expect(isNavigationActive(path, section)).toBe(true));
  it.each([['/reports-old', '/reports'], ['/workspace', '/'], ['/admin/users', '/reports']])('does not select an unrelated section', (path, section) => expect(isNavigationActive(path, section)).toBe(false));
});
