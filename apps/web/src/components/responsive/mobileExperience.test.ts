import {describe,expect,it} from 'vitest';
import primitives from './ResponsivePrimitives.tsx?raw';
import layout from '../../layouts/AppLayout.tsx?raw';
import dashboard from '../../pages/dashboard/DashboardCaseList.tsx?raw';
import filters from '../../pages/dashboard/CaseFilters.tsx?raw';
import details from '../../pages/cases/details/CaseDetailsHeader.tsx?raw';
import reports from '../../pages/reports/cases/CaseReportTable.tsx?raw';

describe('intentional mobile experience',()=>{
  it('provides reusable mobile primitives and reachable primary actions',()=>{
    expect(primitives).toContain('MobileCardList');expect(primitives).toContain('FilterDrawer');
    expect(primitives).toContain('MobileActionBar');expect(primitives).toContain('ResponsiveTable');
    expect(primitives).toContain('ResponsiveFormGrid');expect(layout).toContain('פתיחת קריאה חדשה');
  });
  it('uses cards and a filter drawer instead of compressed desktop tables',()=>{
    expect(dashboard).toMatch(/display\s*:\s*\{\s*md\s*:\s*'none'/);expect(reports).toContain('mobile-report-cards');
    expect(filters).toContain('<FilterDrawer');expect(filters).toContain('badgeContent={active}');
    expect(details).toContain('<MobileActionBar');
  });
});
