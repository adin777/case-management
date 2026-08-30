import { describe, expect, it } from 'vitest';
import tableSource from './CaseReportTable.tsx?raw';
import pageSource from './CaseReportPage.tsx?raw';

describe('case report experience', () => {
  it('uses the shared numeric case formatter and business pills', () => {
    expect(tableSource).toContain('displayCaseNumber');
    expect(tableSource).toContain('<BusinessPill');
  });
  it('keeps filters, export, sorting and pagination connected to backend state', () => {
    expect(pageSource).toContain("['page_size', String(pageSize)]");
    expect(pageSource).toContain('<ExportExcelButton');
    expect(pageSource).toContain('<Pagination');
  });
});
