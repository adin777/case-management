import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Chip, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, Role, User } from '../../../../types';

type Membership = { id: string; user_id: string; user_name: string; role_id: string; role_name_he: string; is_active: boolean };
export function EnvironmentAccessTab({ environment }: { environment: Environment }) {
  const client = useQueryClient(); const [userId, setUserId] = useState(''); const [roleId, setRoleId] = useState('');
  const { data: members = [] } = useQuery({ queryKey: ['environment-members', environment.id], queryFn: () => api<Membership[]>(`/environments/${environment.id}/memberships`) });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users') });
  const { data: roles = [] } = useQuery({ queryKey: ['roles'], queryFn: () => api<Role[]>('/roles') });
  const refresh = () => client.invalidateQueries({ queryKey: ['environment-members', environment.id] });
  async function add() { await api(`/environments/${environment.id}/memberships`, { method: 'POST', body: JSON.stringify({ user_id: userId, group_id: null, role_id: roleId }) }); setUserId(''); setRoleId(''); await refresh(); }
  async function update(member: Membership, patch: object) { await api(`/environments/${environment.id}/memberships/${member.id}`, { method: 'PATCH', body: JSON.stringify(patch) }); await refresh(); }
  async function remove(member: Membership) { await api(`/environments/${environment.id}/memberships/${member.id}`, { method: 'DELETE' }); await refresh(); }
  return <Stack spacing={2}>{members.map((member) => <Paper key={member.id} variant="outlined" sx={{ p: 2 }}><Stack direction={{ xs: 'column', sm: 'row' }} gap={1} alignItems={{ sm: 'center' }}><span style={{ flex: 1 }}><Typography fontWeight={800}>{member.user_name}</Typography><Chip size="small" label={member.is_active ? 'פעיל' : 'מושבת'} color={member.is_active ? 'success' : 'default'}/></span><TextField select size="small" label="תפקיד" value={member.role_id} onChange={(event) => update(member, { role_id: event.target.value })}>{roles.map((role) => <MenuItem key={role.id} value={role.id}>{role.name_he || role.name}{role.is_active ? '' : ' (לא פעיל)'}</MenuItem>)}</TextField><Button onClick={() => update(member, { is_active: !member.is_active })}>{member.is_active ? 'השבתת שיוך' : 'הפעלת שיוך'}</Button><Button color="error" onClick={() => remove(member)}>הסרה מהסביבה</Button></Stack></Paper>)}<Paper variant="outlined" sx={{ p: 2 }}><Stack direction={{ xs: 'column', sm: 'row' }} gap={1}><TextField select fullWidth label="משתמש" value={userId} onChange={(event) => setUserId(event.target.value)}>{users.filter((user) => user.is_active !== false).map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name}</MenuItem>)}</TextField><TextField select fullWidth label="תפקיד" value={roleId} onChange={(event) => setRoleId(event.target.value)}>{roles.filter((role) => role.scope === 'environment' && role.is_active).map((role) => <MenuItem key={role.id} value={role.id}>{role.name_he || role.name}</MenuItem>)}</TextField><Button variant="contained" disabled={!userId || !roleId} onClick={add}>הוספת משתמש</Button></Stack></Paper></Stack>;
}
