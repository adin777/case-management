import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Box, Container, Paper, Stack, Tab, Tabs, Typography } from '@mui/material';
import { api } from '../../api/client';
import type { Environment, Group, Permission, Role, User, UserField } from '../../types';
import { GroupsTab } from './groups/GroupsTab';
import { RoleDialog, type RoleForm } from './roles/RoleDialog';
import { RolesTab } from './roles/RolesTab';
import { UserDialog, type UserForm } from './users/UserDialog';
import { UserDetailsPage } from './users/UserDetailsPage';
import { UsersTab } from './users/UsersTab';
import { UserFieldsTab } from './user-fields/UserFieldsTab';

export function UsersPage() {
  const client = useQueryClient();
  const [tab, setTab] = useState(0); const [error, setError] = useState('');
  const [userOpen, setUserOpen] = useState(false); const [roleOpen, setRoleOpen] = useState(false);
  const [saving, setSaving] = useState(false); const [selectedUser, setSelectedUser] = useState<User>();
  const [selectedRole, setSelectedRole] = useState<Role>();
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users') });
  const { data: groups = [] } = useQuery({ queryKey: ['groups'], queryFn: () => api<Group[]>('/groups') });
  const { data: roles = [] } = useQuery({ queryKey: ['roles'], queryFn: () => api<Role[]>('/roles') });
  const { data: permissions = [] } = useQuery({ queryKey: ['permission-management'], queryFn: () => api<Permission[]>('/permissions/manage') });
  const { data: fields = [] } = useQuery({ queryKey: ['user-fields'], queryFn: () => api<UserField[]>('/user-fields') });
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  async function refresh() { await client.invalidateQueries(); }
  async function createUser(values: UserForm) { setSaving(true); try { await api('/users', { method: 'POST', body: JSON.stringify(values) }); await refresh(); setUserOpen(false); } catch (caught) { setError((caught as Error).message); throw caught; } finally { setSaving(false); } }
  async function saveRole(values: RoleForm) { setSaving(true); try { await api(selectedRole ? `/roles/${selectedRole.id}` : '/roles', { method: selectedRole ? 'PATCH' : 'POST', body: JSON.stringify(values) }); await refresh(); setRoleOpen(false); setSelectedRole(undefined); } catch (caught) { setError((caught as Error).message); throw caught; } finally { setSaving(false); } }
  async function toggle(user: User) { if (!confirm(`${user.is_active ? 'להשבית' : 'להפעיל'} את ${user.display_name}?`)) return; await api(`/users/${user.id}/${user.is_active ? 'deactivate' : 'activate'}`, { method: 'POST' }); await refresh(); }
  return <Container maxWidth="xl"><Stack spacing={3}><Box><Typography variant="h4" fontWeight={800}>משתמשים והרשאות</Typography><Typography color="text.secondary">ניהול זהויות, קבוצות, תפקידים ושדות משתמש</Typography></Box>{error && <Alert severity="error">{error}</Alert>}<Paper variant="outlined"><Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable"><Tab label="משתמשים"/><Tab label="קבוצות משתמשים"/><Tab label="תפקידים והרשאות"/><Tab label="שדות משתמש"/></Tabs></Paper>{tab === 0 && <UsersTab users={users} onCreate={() => setUserOpen(true)} onToggle={toggle} onEdit={setSelectedUser}/>} {tab === 1 && <GroupsTab groups={groups} users={users} roles={roles} environments={environments} onCreated={refresh}/>} {tab === 2 && <RolesTab roles={roles} onCreate={() => { setSelectedRole(undefined); setRoleOpen(true); }} onEdit={(role) => { setSelectedRole(role); setRoleOpen(true); }}/>} {tab === 3 && <UserFieldsTab fields={fields} environments={environments} onSaved={refresh}/>}</Stack><UserDialog open={userOpen} saving={saving} onClose={() => setUserOpen(false)} onSubmit={createUser}/><UserDetailsPage user={selectedUser} environments={environments} onClose={() => setSelectedUser(undefined)}/><RoleDialog open={roleOpen} saving={saving} initial={selectedRole} catalog={permissions} onClose={() => { setRoleOpen(false); setSelectedRole(undefined); }} onSubmit={saveRole}/></Container>;
}
