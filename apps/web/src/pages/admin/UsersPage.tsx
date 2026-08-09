import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Box, Container, Paper, Stack, Tab, Tabs, Typography } from '@mui/material';
import { api } from '../../api/client';
import type { Environment, Group, User, UserField } from '../../types';
import { GroupsTab } from './groups/GroupsTab';
import { DirectorySyncTab } from './users/DirectorySyncTab';
import { UserDialog, type UserForm } from './users/UserDialog';
import { UserDetailsPage } from './users/UserDetailsPage';
import { UsersTab } from './users/UsersTab';
import { UserFieldsTab } from './user-fields/UserFieldsTab';

export function UsersPage() {
  const client = useQueryClient();
  const [tab, setTab] = useState(0); const [error, setError] = useState('');
  const [userOpen, setUserOpen] = useState(false); const [saving, setSaving] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User>();
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users?active_only=false') });
  const { data: groups = [] } = useQuery({ queryKey: ['groups'], queryFn: () => api<Group[]>('/groups') });
  const { data: fields = [] } = useQuery({ queryKey: ['user-fields'], queryFn: () => api<UserField[]>('/user-fields') });
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  async function refresh() { await client.invalidateQueries(); }
  async function createUser(values: UserForm) { setSaving(true); try { await api('/users', { method: 'POST', body: JSON.stringify(values) }); await refresh(); setUserOpen(false); } catch (caught) { setError((caught as Error).message); throw caught; } finally { setSaving(false); } }
  return <Container maxWidth="xl"><Stack spacing={3}>
    <Box><Typography variant="h4" fontWeight={800}>משתמשים והרשאות</Typography><Typography color="text.secondary">ניהול זהויות, קבוצות, סנכרון ושדות משתמש</Typography></Box>
    {error && <Alert severity="error">{error}</Alert>}
    <Paper variant="outlined"><Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable"><Tab label="משתמשים"/><Tab label="קבוצות משתמשים"/><Tab label="משתמשים וסנכרון"/><Tab label="שדות משתמש"/></Tabs></Paper>
    {tab === 0 && <UsersTab users={users} onCreate={() => setUserOpen(true)} onEdit={setSelectedUser}/>}
    {tab === 1 && <GroupsTab groups={groups} users={users} environments={environments} onCreated={refresh}/>}
    {tab === 2 && <DirectorySyncTab onChanged={refresh}/>}
    {tab === 3 && <UserFieldsTab fields={fields} environments={environments} onSaved={refresh}/>}
  </Stack><UserDialog open={userOpen} saving={saving} onClose={() => setUserOpen(false)} onSubmit={createUser}/><UserDetailsPage user={selectedUser} users={users} environments={environments} onSaved={refresh} onClose={() => setSelectedUser(undefined)}/></Container>;
}
