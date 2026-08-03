import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert, Box, Button, Checkbox, Chip, Container, Dialog, DialogActions, DialogContent,
  DialogTitle, FormControlLabel, MenuItem, Paper, Snackbar, Stack, Tab, Tabs, TextField,
  Typography,
} from '@mui/material';
import { api } from '../../../api/client';
import type { Environment, Group, Permission, Role, User } from '../../../types';

type Operation = 'add' | 'remove' | 'replace';

export function PermissionsPage() {
  const client = useQueryClient();
  const [entityTab, setEntityTab] = useState(0);
  const [permissionIds, setPermissionIds] = useState<string[]>([]);
  const [entityIds, setEntityIds] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [active, setActive] = useState('active');
  const [environmentId, setEnvironmentId] = useState('');
  const [roleId, setRoleId] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [editing, setEditing] = useState<Permission>();
  const { data: permissions = [] } = useQuery({ queryKey: ['permission-management'], queryFn: () => api<Permission[]>('/permissions/manage') });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users') });
  const { data: groups = [] } = useQuery({ queryKey: ['groups'], queryFn: () => api<Group[]>('/groups') });
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  const { data: roles = [] } = useQuery({ queryKey: ['roles'], queryFn: () => api<Role[]>('/roles') });
  const filteredUsers = useMemo(() => users.filter((user) => {
    const matchesActive = active === 'all' || (active === 'active') === Boolean(user.is_active);
    const matchesEnvironment = !environmentId || user.memberships?.some((item) => item.environment_id === environmentId);
    const matchesRole = !roleId || user.memberships?.some((item) => item.role_id === roleId);
    return matchesActive && matchesEnvironment && matchesRole && `${user.display_name} ${user.email}`.toLowerCase().includes(search.toLowerCase());
  }), [users, active, environmentId, roleId, search]);
  const filteredGroups = groups.filter((group) => (active === 'all' || (active === 'active') === group.is_active) && `${group.name} ${group.description || ''}`.toLowerCase().includes(search.toLowerCase()));
  const toggle = (values: string[], value: string, setter: (next: string[]) => void) => setter(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  async function bulk(operation: Operation) {
    if (!permissionIds.length || !entityIds.length) return;
    const entityLabel = entityTab === 0 ? 'משתמשים' : 'קבוצות';
    if (!confirm(`האם לבצע ${operation === 'add' ? 'הוספה' : operation === 'remove' ? 'הסרה' : 'החלפה'} של ${permissionIds.length} הרשאות עבור ${entityIds.length} ${entityLabel}?`)) return;
    try {
      const result = await api<{ created: number; removed: number; unchanged: number }>(`/permissions/bulk/${entityTab === 0 ? 'users' : 'groups'}`, {
        method: 'POST', body: JSON.stringify({ permission_codes: permissionIds, environment_id: environmentId || null, operation, [entityTab === 0 ? 'user_ids' : 'group_ids']: entityIds }),
      });
      setMessage(`נוספו ${result.created}, הוסרו ${result.removed}, ללא שינוי ${result.unchanged}`);
    } catch (caught) { setError((caught as Error).message); }
  }
  async function savePermission() {
    if (!editing) return;
    await api(`/permissions/${editing.code}`, { method: 'PATCH', body: JSON.stringify(editing) });
    await client.invalidateQueries({ queryKey: ['permission-management'] });
    setEditing(undefined); setMessage('ההרשאה עודכנה בהצלחה');
  }
  return <Container maxWidth="xl"><Stack spacing={2}>
    <Box><Typography variant="h4" fontWeight={800}>ניהול הרשאות גורף</Typography><Typography color="text.secondary">בחירת הרשאות ומשתמשים או קבוצות, והחלה מרוכזת עם Scope ואימות Backend</Typography></Box>
    {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
    <Box className="permission-grid">
      <Paper variant="outlined" sx={{ p: 2 }}><Typography variant="h6" fontWeight={800}>הרשאות ({permissionIds.length} נבחרו)</Typography>
        <Stack spacing={1} sx={{ mt: 1, maxHeight: 570, overflow: 'auto' }}>{permissions.map((permission) => <Paper key={permission.code} variant="outlined" sx={{ p: 1.25, opacity: permission.is_active === false ? .55 : 1 }}>
          <Stack direction="row" alignItems="flex-start"><Checkbox checked={permissionIds.includes(permission.code)} onChange={() => toggle(permissionIds, permission.code, setPermissionIds)} /><Box flex={1}><Typography fontWeight={700}>{permission.name_he || permission.code}</Typography><Typography variant="body2">{permission.description_he || permission.description}</Typography><Typography variant="caption" color="text.secondary">{permission.code} · {permission.category} · {permission.scope === 'system' ? 'מערכתית' : 'סביבתית'}</Typography><Stack direction="row" gap={.5} mt={.5}><Chip size="small" label={`${permission.user_count || 0} משתמשים`} /><Chip size="small" label={`${permission.group_count || 0} קבוצות`} /><Button size="small" onClick={() => setEditing(permission)}>עריכה</Button></Stack></Box></Stack>
        </Paper>)}</Stack>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2 }}><Tabs value={entityTab} onChange={(_, value) => { setEntityTab(value); setEntityIds([]); }}><Tab label="משתמשים"/><Tab label="קבוצות משתמשים"/></Tabs>
        <Stack direction={{ xs: 'column', md: 'row' }} gap={1} my={2}><TextField label="חיפוש לפי שם או מייל" value={search} onChange={(event) => setSearch(event.target.value)} fullWidth/><TextField select label="מצב" value={active} onChange={(event) => setActive(event.target.value)} sx={{ minWidth: 130 }}><MenuItem value="all">הכול</MenuItem><MenuItem value="active">פעילים</MenuItem><MenuItem value="inactive">לא פעילים</MenuItem></TextField></Stack>
        {entityTab === 0 && <Stack direction={{ xs: 'column', md: 'row' }} gap={1} mb={2}><TextField select label="סביבה" value={environmentId} onChange={(event) => setEnvironmentId(event.target.value)} fullWidth><MenuItem value="">כל הסביבות</MenuItem>{environments.map((env) => <MenuItem key={env.id} value={env.id}>{env.name_he}</MenuItem>)}</TextField><TextField select label="תפקיד" value={roleId} onChange={(event) => setRoleId(event.target.value)} fullWidth><MenuItem value="">כל התפקידים</MenuItem>{roles.map((role) => <MenuItem key={role.id} value={role.id}>{role.name}</MenuItem>)}</TextField></Stack>}
        <Stack sx={{ maxHeight: 470, overflow: 'auto' }}>{(entityTab === 0 ? filteredUsers : filteredGroups).map((entity) => <FormControlLabel key={entity.id} control={<Checkbox checked={entityIds.includes(entity.id)} onChange={() => toggle(entityIds, entity.id, setEntityIds)} />} label={entityTab === 0 ? `${(entity as User).display_name} · ${(entity as User).email}` : `${(entity as Group).name} · ${(entity as Group).member_count} חברים`} />)}</Stack>
      </Paper>
    </Box>
    <Paper className="bulk-toolbar" elevation={4}><Typography fontWeight={700}>נבחרו {entityIds.length} ישויות ו־{permissionIds.length} הרשאות</Typography><Stack direction="row" flexWrap="wrap" gap={1}><Button variant="contained" disabled={!entityIds.length || !permissionIds.length} onClick={() => bulk('add')}>הוספת הרשאות</Button><Button color="error" variant="outlined" disabled={!entityIds.length || !permissionIds.length} onClick={() => bulk('remove')}>הסרת הרשאות</Button><Button variant="outlined" disabled={!entityIds.length || !permissionIds.length} onClick={() => bulk('replace')}>החלפת הרשאות</Button><Button onClick={() => { setEntityIds([]); setPermissionIds([]); }}>ניקוי בחירה</Button></Stack></Paper>
  </Stack><Snackbar open={!!message} autoHideDuration={5000} onClose={() => setMessage('')} message={message}/>
  <Dialog open={!!editing} onClose={() => setEditing(undefined)} fullWidth>{editing && <><DialogTitle>עריכת הרשאה</DialogTitle><DialogContent><Stack spacing={2} mt={1}><TextField label="קוד טכני" value={editing.code} disabled/><TextField label="שם בעברית" value={editing.name_he || ''} onChange={(e) => setEditing({ ...editing, name_he: e.target.value })}/><TextField label="תיאור בעברית" multiline value={editing.description_he || ''} onChange={(e) => setEditing({ ...editing, description_he: e.target.value })}/><TextField label="קטגוריה בעברית" value={editing.category || ''} onChange={(e) => setEditing({ ...editing, category: e.target.value })}/><FormControlLabel control={<Checkbox checked={editing.is_active !== false} onChange={(e) => setEditing({ ...editing, is_active: e.target.checked })}/>} label="הרשאה פעילה"/></Stack></DialogContent><DialogActions><Button onClick={() => setEditing(undefined)}>ביטול</Button><Button variant="contained" onClick={savePermission}>שמירה</Button></DialogActions></>}</Dialog>
  </Container>;
}
