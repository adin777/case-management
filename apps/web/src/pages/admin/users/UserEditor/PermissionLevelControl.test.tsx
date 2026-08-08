import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { PermissionLevelControl } from './PermissionLevelControl';

describe('PermissionLevelControl', () => {
  it('shows inheritance and business access levels in Hebrew', () => {
    const html = renderToStaticMarkup(<PermissionLevelControl inherit value="inherit" onChange={() => undefined}/>);
    expect(html).toContain('ירושה'); expect(html).toContain('ללא'); expect(html).toContain('צפייה'); expect(html).toContain('עריכה');
  });
  it('does not expose technical permission codes', () => {
    const html = renderToStaticMarkup(<PermissionLevelControl value="view" onChange={() => undefined}/>);
    expect(html).not.toContain('system.users'); expect(html).not.toContain('case.update');
  });
});
