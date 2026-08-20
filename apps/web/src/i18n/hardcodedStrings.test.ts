import {describe,expect,it} from 'vitest';
import loginSource from '../pages/auth/LoginPage.tsx?raw';
import registerSource from '../pages/auth/RegisterPage.tsx?raw';
import createCaseSource from '../pages/cases/CreateCasePage.tsx?raw';

const migrated=[['LoginPage',loginSource],['RegisterPage',registerSource],['CreateCasePage',createCaseSource]] as const;

describe('central UI translation guard',()=>{
  it.each(migrated)('does not add hardcoded Hebrew user text to %s',(_name,source)=>{
    expect(source).not.toMatch(/[א-ת]{2,}/);
  });
});
