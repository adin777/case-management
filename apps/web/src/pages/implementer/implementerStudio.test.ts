import {describe,expect,it} from 'vitest';
import studio from './ImplementerStudioPage.tsx?raw';
import layout from '../../layouts/AppLayout.tsx?raw';

describe('implementer studio landing',()=>{
  it('collects existing configuration surfaces without a second data model',()=>{
    expect(studio).toContain("'/environments'");expect(studio).toContain("'/global-case-fields?include_inactive=true'");
    expect(studio).toContain('בדיקת תקינות');expect(studio).toContain('שדות בחירה פעילים ללא אפשרויות פעילות');
    expect(layout).toContain("url: '/implementer'");expect(layout).toContain('canImplement');
  });
});
