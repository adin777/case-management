import {describe,expect,it} from 'vitest';
import environmentsSource from './environments/EnvironmentList.tsx?raw';
import approvalsSource from '../approvals/PendingApprovalsPage.tsx?raw';
import layoutSource from '../../layouts/AppLayout.tsx?raw';
import bannerSource from '../../layouts/ImpersonationBanner.tsx?raw';

describe('modern admin screens',()=>{
  it('uses the shared header, filters and database overview for environments',()=>{expect(environmentsSource).toContain('<ScreenHeader');expect(environmentsSource).toContain('case_count');expect(environmentsSource).toContain('manager_names');expect(environmentsSource).toContain("replace(/\\D/g,'')")});
  it('keeps approval decisions in the modern table and detail panel',()=>{expect(approvalsSource).toContain('<Table');expect(approvalsSource).toContain('approver_name');expect(approvalsSource).toContain('displayCaseNumber');expect(approvalsSource).toContain("value:'approved'");expect(approvalsSource).toContain("value:'rejected'")});
  it('has one persistent impersonation surface with both identities and no logout',()=>{expect(layoutSource).toContain('<ImpersonationBanner');expect(layoutSource.match(/<ImpersonationBanner/g)).toHaveLength(1);expect(bannerSource).toContain('real_actor_name');expect(bannerSource).toContain('impersonated_user_name');expect(bannerSource).toContain('סיום התחזות');expect(bannerSource).not.toContain('logout')});
});
