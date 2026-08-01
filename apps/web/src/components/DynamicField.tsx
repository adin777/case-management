import {Checkbox,FormControl,FormControlLabel,InputLabel,MenuItem,Select,TextField} from '@mui/material';
import type {Field,User} from '../types';

export function DynamicField({field,value,onChange,users=[]}:{field:Field;value:unknown;onChange:(value:unknown)=>void;users?:User[]}) {
  if(field.field_type==='boolean') return <FormControlLabel control={<Checkbox checked={Boolean(value)} onChange={e=>onChange(e.target.checked)}/>} label={field.label_he}/>;
  if(field.field_type==='single_select'||field.field_type==='user') return <FormControl required={field.is_required}><InputLabel>{field.label_he}</InputLabel><Select label={field.label_he} value={String(value||'')} onChange={e=>onChange(e.target.value)}>{field.field_type==='user'?users.map(u=><MenuItem key={u.id} value={u.id}>{u.display_name}</MenuItem>):field.configuration_json.options?.map(option=><MenuItem key={option} value={option}>{option}</MenuItem>)}</Select></FormControl>;
  const type={number:'number',date:'date',datetime:'datetime-local'}[field.field_type]||'text';
  return <TextField label={field.label_he} required={field.is_required} type={type} multiline={field.field_type==='long_text'} minRows={field.field_type==='long_text'?3:undefined} value={value??''} onChange={e=>onChange(field.field_type==='number'?Number(e.target.value):e.target.value)} slotProps={type==='date'||type==='datetime-local'?{inputLabel:{shrink:true}}:undefined}/>;
}
