import { describe, expect, it } from 'vitest';
import type { User } from '../../../types';
import { filterUsers } from './userFilters';

const rows=[
  {id:'1',display_name:'נועה',email:'noa@example.com',user_principal_name:'noa@example.com',status:'active',source:'manual',department:'רכש',job_title:'קניינית'},
  {id:'2',display_name:'דן',email:'dan@example.com',user_principal_name:'dan@example.com',status:'inactive',source:'excel',department:'IT',job_title:'תמיכה'},
] as User[];

describe('user filters',()=>{
  it('combines the staged filter fields',()=>expect(filterUsers(rows,{status:'active',source:'manual',department:'רכש',jobTitle:'קניינית',search:'noa'}).map(row=>row.id)).toEqual(['1']));
  it('returns all users after reset values',()=>expect(filterUsers(rows,{status:'',source:'',department:'',jobTitle:'',search:''})).toHaveLength(2));
});
