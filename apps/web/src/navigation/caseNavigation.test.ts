import {describe,expect,it,vi} from 'vitest';
import {openCase} from './caseNavigation';
import details from '../pages/cases/CaseDetailsPage.tsx?raw';
import reports from '../pages/reports/OperationalReportPage.tsx?raw';

describe('case return navigation',()=>{
  it('preserves the exact report route and query string',()=>{
    const navigate=vi.fn();
    openCase(navigate,{pathname:'/reports/cases',search:'?page=3&status=open'} as never,'case-id','חזרה לדוח');
    expect(navigate).toHaveBeenCalledWith('/cases/case-id',{state:{returnTo:'/reports/cases?page=3&status=open',returnLabel:'חזרה לדוח'}});
  });
  it('renders a real mobile back action and report origins use shared state',()=>{
    expect(details).toContain('onBack={goBack}');
    expect(details).toContain("navigate(state.returnTo)");
    expect(reports).toContain("'חזרה לדוח'");
  });
});
