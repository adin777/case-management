import {FormEvent,useState} from 'react';
import {Link,useNavigate} from 'react-router-dom';
import {useQueryClient} from '@tanstack/react-query';
import {Alert,Box,Button,Card,CardContent,CircularProgress,Stack,TextField,Typography} from '@mui/material';
import {useTranslation} from 'react-i18next';
import {ApiError,getCurrentUser,register,token} from '../../api/client';

export function RegisterPage(){
  const {t}=useTranslation();const nav=useNavigate();const qc=useQueryClient();
  const[name,setName]=useState('');const[email,setEmail]=useState('');const[password,setPassword]=useState('');const[confirm,setConfirm]=useState('');const[error,setError]=useState('');const[loading,setLoading]=useState(false);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setError('');if(!name.trim()||!email.trim()||!password||!confirm){setError(t('common.required'));return}if(password!==confirm){setError(t('register.mismatch'));return}setLoading(true);try{const result=await register(name,email,password);token.set(result.access_token,result.refresh_token);const user=await getCurrentUser();qc.setQueryData(['me'],user);nav('/',{replace:true})}catch(caught){setError(caught instanceof ApiError?caught.message:t('errors.server'))}finally{setLoading(false)}}
  return <Box className="login-art"><Card sx={{width:{xs:'92%',sm:500},p:2}}><CardContent><Box component="form" noValidate onSubmit={submit}><Stack spacing={2.5}><Typography variant="h4">{t('register.title')}</Typography>{error&&<Alert severity="error">{error}</Alert>}<TextField label={t('register.name')} value={name} onChange={e=>setName(e.target.value)}/><TextField label={t('register.email')} type="email" value={email} onChange={e=>setEmail(e.target.value)}/><TextField label={t('register.password')} type="password" value={password} onChange={e=>setPassword(e.target.value)} helperText={t('register.passwordHint')}/><TextField label={t('register.confirm')} type="password" value={confirm} onChange={e=>setConfirm(e.target.value)}/><Button type="submit" variant="contained" size="large" disabled={loading}>{loading?<><CircularProgress size={20} color="inherit" sx={{ml:1}}/>{t('register.submitting')}</>:t('register.submit')}</Button><Typography textAlign="center"><Link to="/login">{t('register.back')}</Link></Typography></Stack></Box></CardContent></Card></Box>;
}
