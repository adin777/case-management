import { useEffect, useState } from 'react';
import { Alert, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, Grid, Stack, TextField } from '@mui/material';
import { validateUser, type FieldErrors, type UserForm } from './userValidation';

export type { UserForm } from './userValidation';
const empty:UserForm={first_name:'',last_name:'',display_name:'',email:'',user_principal_name:'',department:'',job_title:'',phone:'',mobile_phone:'',employee_id:'',computer_identifier:'',password:'',is_active:true,is_system_admin:false};
export function UserDialog({open,saving,onClose,onSubmit}:{open:boolean;saving:boolean;onClose:()=>void;onSubmit:(values:UserForm)=>Promise<void>}) {
  const[values,setValues]=useState(empty); const[errors,setErrors]=useState<FieldErrors>({}); const[submitError,setSubmitError]=useState('');
  useEffect(()=>{if(!open){setValues(empty);setErrors({});setSubmitError('')}},[open]);
  const update=(key:keyof UserForm,value:string|boolean)=>{setValues(current=>({...current,[key]:value}));setErrors(current=>({...current,[key]:undefined}));};
  const field=(key:keyof UserForm,label:string)=><TextField fullWidth label={label} value={String(values[key])} error={Boolean(errors[key])} helperText={errors[key]} onChange={event=>update(key,event.target.value)}/>;
  async function submit(event:React.FormEvent){
    event.preventDefault(); const validation=validateUser(values); setErrors(validation); setSubmitError('');
    if(Object.keys(validation).length) return;
    try { await onSubmit({...values,email:values.email.trim(),user_principal_name:values.user_principal_name.trim()||values.email.trim()}); }
    catch(caught){setSubmitError((caught as Error).message||'שמירת המשתמש נכשלה');}
  }
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="md"><Stack component="form" onSubmit={submit} noValidate><DialogTitle>יצירת משתמש ידני</DialogTitle><DialogContent>{submitError&&<Alert severity="error" sx={{mb:2}}>{submitError}</Alert>}<Grid container spacing={2} sx={{pt:1}}><Grid size={{xs:12,sm:6}}>{field('first_name','שם פרטי')}</Grid><Grid size={{xs:12,sm:6}}>{field('last_name','שם משפחה')}</Grid><Grid size={{xs:12,sm:6}}>{field('display_name','שם תצוגה')}</Grid><Grid size={{xs:12,sm:6}}>{field('email','דוא״ל')}</Grid><Grid size={{xs:12,sm:6}}>{field('user_principal_name','שם משתמש / UPN (ברירת מחדל: דוא״ל)')}</Grid><Grid size={{xs:12,sm:6}}>{field('department','מחלקה')}</Grid><Grid size={{xs:12,sm:6}}>{field('job_title','תפקיד ארגוני')}</Grid><Grid size={{xs:12,sm:6}}>{field('employee_id','מספר עובד')}</Grid><Grid size={{xs:12,sm:6}}>{field('phone','טלפון')}</Grid><Grid size={{xs:12,sm:6}}>{field('mobile_phone','טלפון נייד')}</Grid><Grid size={{xs:12,sm:6}}>{field('computer_identifier','מזהה מחשב')}</Grid><Grid size={{xs:12,sm:6}}><TextField fullWidth label="סיסמה זמנית" type="password" value={values.password} error={Boolean(errors.password)} helperText={errors.password||'לפחות 8 תווים'} onChange={event=>update('password',event.target.value)}/></Grid></Grid><FormControlLabel control={<Checkbox checked={values.is_active} onChange={event=>update('is_active',event.target.checked)}/>} label="משתמש פעיל"/><FormControlLabel control={<Checkbox checked={values.is_system_admin} onChange={event=>update('is_system_admin',event.target.checked)}/>} label="מנהל מערכת"/></DialogContent><DialogActions><Button onClick={onClose}>ביטול</Button><Button type="submit" variant="contained" disabled={saving}>{saving?'שומר…':'שמירה'}</Button></DialogActions></Stack></Dialog>;
}
