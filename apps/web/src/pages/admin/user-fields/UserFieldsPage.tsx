import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Container, Stack, Typography } from '@mui/material';
import { api } from '../../../api/client';
import type { Environment, UserField } from '../../../types';
import { UserFieldsTab } from './UserFieldsTab';

export function UserFieldsPage(){
  const client=useQueryClient();
  const{data:fields=[]}=useQuery({queryKey:['user-fields'],queryFn:()=>api<UserField[]>('/user-fields')});
  const{data:environments=[]}=useQuery({queryKey:['environments'],queryFn:()=>api<Environment[]>('/environments')});
  return <Container maxWidth="lg"><Stack spacing={3}><div><Typography variant="h4">שדות משתמש</Typography><Typography color="text.secondary">שדות גלובליים החלים על כלל המשתמשים במערכת</Typography></div><UserFieldsTab fields={fields} environments={environments} onSaved={()=>client.invalidateQueries({queryKey:['user-fields']})}/></Stack></Container>;
}
