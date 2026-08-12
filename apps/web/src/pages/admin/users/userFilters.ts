import type { User } from '../../../types';
export type UserFilters={status:string;source:string;department:string;jobTitle:string;search:string};
export const emptyUserFilters:UserFilters={status:'active',source:'',department:'',jobTitle:'',search:''};
export function filterUsers(users:User[],filters:UserFilters){const term=filters.search.trim().toLowerCase();return users.filter(user=>(!filters.status||user.status===filters.status)&&(!filters.source||user.source===filters.source)&&(!filters.department||user.department===filters.department)&&(!filters.jobTitle||user.job_title===filters.jobTitle)&&(!term||`${user.display_name} ${user.email} ${user.user_principal_name||''}`.toLowerCase().includes(term)));}
