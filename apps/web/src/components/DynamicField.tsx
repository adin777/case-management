import {Checkbox,FormControl,FormControlLabel,InputLabel,MenuItem,Select,TextField} from '@mui/material';
import type {Field,User} from '../types';

export function DynamicField({field,value,onChange,users=[]}:{field:Field;value:unknown;onChange:(value:unknown)=>void;users?:User[]}) {
  if(field.field_type==='boolean') return <FormControlLabel control={<Checkbox checked={Boolean(value)} onChange={e=>onChange(e.target.checked)}/>} label={field.label_he}/>;
  if(['single_select','multi_select','user'].includes(field.field_type)) return <FormControl required={field.is_required}><InputLabel>{field.label_he}</InputLabel><Select multiple={field.field_type==='multi_select'} label={field.label_he} value={field.field_type==='multi_select'?(value as string[]||[]):String(value||'')} onChange={e=>onChange(e.target.value)}>{field.field_type==='user'?users.map(u=><MenuItem key={u.id} value={u.id}>{u.display_name}</MenuItem>):field.configuration_json.options?.filter(option=>typeof option==='string'||option.is_active!==false).map(option=>{const id=typeof option==='string'?option:option.id;const label=typeof option==='string'?option:option.label_he;return <MenuItem key={id} value={id}>{label}</MenuItem>})}</Select></FormControl>;
  const type={number:'number',date:'date',datetime:'datetime-local'}[field.field_type]||'text';
  return <TextField label={field.label_he} required={field.is_required} type={type} multiline={['long_text','textarea'].includes(field.field_type)} minRows={['long_text','textarea'].includes(field.field_type)?3:undefined} value={value??''} onChange={e=>onChange(field.field_type==='number'?Number(e.target.value):e.target.value)} slotProps={type==='date'||type==='datetime-local'?{inputLabel:{shrink:true}}:undefined}/>;
}
