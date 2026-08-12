import { describe, expect, it } from 'vitest';
import { validateUser, type UserForm } from './userValidation';

const valid:UserForm={first_name:'נועה',last_name:'ישראלי',display_name:'נועה ישראלי',email:'noa@example.com',user_principal_name:'',department:'',job_title:'',phone:'',mobile_phone:'',employee_id:'',computer_identifier:'',password:'Password1!',is_active:true,is_system_admin:false};

describe('manual user validation',()=>{
  it('explains each required or invalid field',()=>{const errors=validateUser({...valid,display_name:'',email:'bad',password:'short'});expect(errors.display_name).toContain('חובה');expect(errors.email).toContain('תקינה');expect(errors.password).toContain('8');});
  it('accepts a valid email and password without requiring UPN',()=>expect(validateUser(valid)).toEqual({}));
});
