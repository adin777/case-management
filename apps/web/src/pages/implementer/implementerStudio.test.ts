import {describe,expect,it} from 'vitest';
import studio from './ImplementerStudioPage.tsx?raw';
import layout from '../../layouts/AppLayout.tsx?raw';

describe('implementer studio landing',()=>{
  it('collects existing configuration surfaces without a second data model',()=>{
    expect(studio).toContain("'/environments'");expect(studio).toContain("'/global-case-fields?include_inactive=true'");
    expect(studio).toContain('שדות בחירה פעילים ללא אפשרויות פעילות');
    expect((studio.match(/url:'\/admin\//g)||[])).toHaveLength(4);
    expect(studio).not.toContain("title:'אוטומציות'");expect(studio).not.toContain("title:'אישורים'");
    expect(layout).toContain("url: '/implementer'");expect(layout).toContain('canImplement');
    expect(layout).not.toContain("url: '/admin/environments'");expect(layout).not.toContain("url: '/admin/users'");
  });
});
