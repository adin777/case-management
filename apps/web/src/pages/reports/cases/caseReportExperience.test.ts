import { describe, expect, it } from 'vitest';
import tableSource from './CaseReportTable.tsx?raw';
import pageSource from './CaseReportPage.tsx?raw';
import filtersSource from './CaseReportFilters.tsx?raw';
import operationalSource from '../OperationalReportPage.tsx?raw';
import compactFilters from '../../../components/filters/CompactFilterPanel.tsx?raw';

describe('case report experience', () => {
  it('uses the shared numeric case formatter and business pills', () => {
    expect(tableSource).toContain('displayCaseNumber');
    expect(tableSource).toContain('<BusinessPill');
    expect(tableSource).toContain('<CardActionArea');
    expect(tableSource).toContain("openCase(navigate,location,id,'חזרה לדוח')");
  });
  it('keeps filters, export, sorting and pagination connected to backend state', () => {
    expect(pageSource).toContain("['page_size', String(pageSize)]");
    expect(pageSource).toContain('<ExportExcelButton');
    expect(pageSource).toContain('<Pagination');
  });
  it('uses one compact responsive filter pattern and mobile report drill-down', () => {
    expect(filtersSource).toContain('<CompactFilterPanel');
    expect(operationalSource).toContain('<CompactFilterPanel');
    expect(operationalSource).toContain('<CardActionArea');
    expect(compactFilters).toContain('anchor="bottom"');
    expect(compactFilters).toContain('<Collapse');
    expect(compactFilters).toContain('badgeContent={activeCount}');
  });
});
