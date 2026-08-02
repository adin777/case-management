import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Add, AdminPanelSettings, Group as GroupIcon, Person } from '@mui/icons-material';
import {
  Alert, Avatar, Box, Button, Checkbox, Chip, Container, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControlLabel, MenuItem, Paper, Stack, Tab, Table,
  TableBody, TableCell, TableHead, TableRow, Tabs, TextField, Typography,
} from '@mui/material';
import { api } from '../../api/client';
import type { Environment, Group, Permission, Role, User, UserField } from '../../types';

type DialogKind = 'user' | 'group' | 'role' | 'field' | null;

export function UsersPage() {
  const client = useQueryClient();
  const [tab, setTab] = useState(0);
  const [dialog, setDialog] = useState<DialogKind>(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [memberUserId, setMemberUserId] = useState('');
  const [groupEnvironmentId, setGroupEnvironmentId] = useState('');
  const [groupRoleId, setGroupRoleId] = useState('');
  const [userForm, setUserForm] = useState({ display_name: '', email: '', password: '', is_active: true, is_system_admin: false });
  const [groupForm, setGroupForm] = useState({ name: '', description: '', is_active: true });
  const [roleForm, setRoleForm] = useState({ code: '', name: '', description: '', scope: 'environment', permissions: [] as string[] });
  const [fieldForm, setFieldForm] = useState({ key: '', label_he: '', label_en: '', field_type: 'short_text', is_required: false, is_active: true, options_json: [] as string[], validation_json: {}, sort_order: 0 });
  const { data: users = [], isLoading: usersLoading } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users') });
  const { data: groups = [] } = useQuery({ queryKey: ['groups'], queryFn: () => api<Group[]>('/groups'), enabled: tab === 1 });
  const { data: roles = [] } = useQuery({ queryKey: ['roles'], queryFn: () => api<Role[]>('/roles'), enabled: tab === 1 || tab === 2 });
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments'), enabled: tab === 1 });
  const { data: permissionCatalog = [] } = useQuery({ queryKey: ['permissions'], queryFn: () => api<Permission[]>('/permissions'), enabled: tab === 2 || dialog === 'role' });
  const { data: fields = [] } = useQuery({ queryKey: ['user-fields'], queryFn: () => api<UserField[]>('/user-fields'), enabled: tab === 3 });

  const visibleUsers = useMemo(() => users.filter((item) => `${item.display_name} ${item.email}`.toLowerCase().includes(search.toLowerCase())), [users, search]);
  const save = useMutation({
    mutationFn: async () => {
      if (dialog === 'user') return api('/users', { method: 'POST', body: JSON.stringify(userForm) });
      if (dialog === 'group') return api('/groups', { method: 'POST', body: JSON.stringify(groupForm) });
      if (dialog === 'role') return api('/roles', { method: 'POST', body: JSON.stringify(roleForm) });
      return api('/user-fields', { method: 'POST', body: JSON.stringify({ ...fieldForm, default_value_json: null }) });
    },
    onSuccess: () => { setDialog(null); setError(''); client.invalidateQueries(); },
    onError: (caught) => setError((caught as Error).message),
  });
  const toggleUser = async (item: User) => {
    if (!confirm(`${item.is_active ? 'להשבית' : 'להפעיל'} את ${item.display_name}?`)) return;
    await api(`/users/${item.id}/${item.is_active ? 'deactivate' : 'activate'}`, { method: 'POST' });
    client.invalidateQueries({ queryKey: ['users'] });
  };
  async function addMember() {
    await api(`/groups/${selectedGroupId}/members`, { method: 'POST', body: JSON.stringify({ user_id: memberUserId }) });
    setMemberUserId(''); setError(''); client.invalidateQueries({ queryKey: ['groups'] }); client.invalidateQueries({ queryKey: ['users'] });
  }
  async function assignGroupRole() {
    await api(`/groups/${selectedGroupId}/roles`, { method: 'POST', body: JSON.stringify({ environment_id: groupEnvironmentId, role_id: groupRoleId }) });
    setError('');
  }

  return <Container maxWidth="xl">
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" fontWeight={800}>משתמשים והרשאות</Typography>
        <Typography color="text.secondary">ניהול זהויות, קבוצות ותפקידי גישה מכל מקום מרכזי אחד</Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      <Paper variant="outlined">
        <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable">
          <Tab label="משתמשים" /><Tab label="קבוצות משתמשים" /><Tab label="תפקידים והרשאות" /><Tab label="שדות משתמש" />
        </Tabs>
      </Paper>

      {tab === 0 && <Stack spacing={2}>
        <Stack direction={{ xs: 'column', sm: 'row' }} gap={2} justifyContent="space-between">
          <TextField label="חיפוש לפי שם או מייל" value={search} onChange={(event) => setSearch(event.target.value)} sx={{ minWidth: 300 }} />
          <Button variant="contained" startIcon={<Add />} onClick={() => setDialog('user')}>יצירת משתמש</Button>
        </Stack>
        <Paper variant="outlined" sx={{ overflowX: 'auto' }}>
          <Table>
            <TableHead><TableRow><TableCell>משתמש</TableCell><TableCell>סטטוס</TableCell><TableCell>הרשאת מערכת</TableCell><TableCell>קבוצות</TableCell><TableCell>סביבות ותפקידים</TableCell><TableCell>התחברות אחרונה</TableCell><TableCell>פעולות</TableCell></TableRow></TableHead>
            <TableBody>
              {!usersLoading && visibleUsers.length === 0 && <TableRow><TableCell colSpan={7} align="center">לא נמצאו משתמשים</TableCell></TableRow>}
              {visibleUsers.map((item) => <TableRow key={item.id} hover>
                <TableCell><Stack direction="row" spacing={1.5} alignItems="center"><Avatar>{item.display_name[0]}</Avatar><Box><Typography fontWeight={700}>{item.display_name}</Typography><Typography variant="body2" color="text.secondary">{item.email}</Typography></Box></Stack></TableCell>
                <TableCell><Chip size="small" color={item.is_active ? 'success' : 'default'} label={item.is_active ? 'פעיל' : 'מושבת'} /></TableCell>
                <TableCell>{item.is_system_admin ? <Chip icon={<AdminPanelSettings />} color="primary" label="מנהל מערכת" /> : 'משתמש רגיל'}</TableCell>
                <TableCell>{item.groups?.map((group) => <Chip key={group.id} size="small" label={group.name} sx={{ m: .25 }} />)}</TableCell>
                <TableCell>{item.memberships?.map((membership) => <Chip key={`${membership.environment_id}-${membership.role_id}`} size="small" variant="outlined" label={`${membership.environment_name} · ${membership.role_name}`} sx={{ m: .25 }} />)}</TableCell>
                <TableCell>{item.last_login_at ? new Date(item.last_login_at).toLocaleString('he-IL') : 'טרם התחבר'}</TableCell>
                <TableCell><Button size="small" color={item.is_active ? 'warning' : 'success'} onClick={() => toggleUser(item)}>{item.is_active ? 'השבתה' : 'הפעלה'}</Button></TableCell>
              </TableRow>)}
            </TableBody>
          </Table>
        </Paper>
      </Stack>}

      {tab === 1 && <Stack spacing={2}>
        <Button sx={{ alignSelf: 'flex-start' }} variant="contained" startIcon={<GroupIcon />} onClick={() => setDialog('group')}>קבוצה חדשה</Button>
        {groups.length === 0 ? <Paper sx={{ p: 5, textAlign: 'center' }}>אין קבוצות. צרו קבוצה ראשונה לצוות עבודה.</Paper> : groups.map((group) => <Paper key={group.id} variant="outlined" sx={{ p: 2, cursor: 'pointer', borderColor: selectedGroupId === group.id ? 'primary.main' : undefined }} onClick={() => setSelectedGroupId(group.id)}><Stack direction="row" justifyContent="space-between"><Box><Typography fontWeight={700}>{group.name}</Typography><Typography color="text.secondary">{group.description || 'ללא תיאור'}</Typography></Box><Chip label={`${group.member_count} חברים`} /></Stack></Paper>)}
        {selectedGroupId && <Paper variant="outlined" sx={{ p: 2 }}><Typography variant="h6" fontWeight={800}>ניהול הקבוצה שנבחרה</Typography><Stack spacing={2} sx={{ mt: 2 }}><Stack direction={{ xs: 'column', md: 'row' }} spacing={1}><TextField select fullWidth label="משתמש להוספה" value={memberUserId} onChange={(event) => setMemberUserId(event.target.value)}>{users.map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name} · {user.email}</MenuItem>)}</TextField><Button variant="outlined" disabled={!memberUserId} onClick={addMember}>הוספה לקבוצה</Button></Stack><Stack direction={{ xs: 'column', md: 'row' }} spacing={1}><TextField select fullWidth label="סביבה" value={groupEnvironmentId} onChange={(event) => setGroupEnvironmentId(event.target.value)}>{environments.map((environment) => <MenuItem key={environment.id} value={environment.id}>{environment.name_he}</MenuItem>)}</TextField><TextField select fullWidth label="Role" value={groupRoleId} onChange={(event) => setGroupRoleId(event.target.value)}>{roles.filter((role) => role.scope === 'environment').map((role) => <MenuItem key={role.id} value={role.id}>{role.name}</MenuItem>)}</TextField><Button variant="contained" disabled={!groupEnvironmentId || !groupRoleId} onClick={assignGroupRole}>שיוך Role לקבוצה</Button></Stack></Stack></Paper>}
      </Stack>}

      {tab === 2 && <Stack spacing={2}>
        <Button sx={{ alignSelf: 'flex-start' }} variant="contained" startIcon={<Add />} onClick={() => setDialog('role')}>תפקיד חדש</Button>
        {roles.map((role) => <Paper key={role.id} variant="outlined" sx={{ p: 2 }}><Stack spacing={1}><Stack direction="row" justifyContent="space-between"><Box><Typography fontWeight={800}>{role.name}</Typography><Typography color="text.secondary">{role.description || role.code}</Typography></Box><Chip label={role.scope === 'system' ? 'מערכתי' : 'סביבתי'} /></Stack><Box>{role.permissions.map((permission) => <Chip key={permission} size="small" variant="outlined" label={permission} sx={{ m: .25 }} />)}</Box></Stack></Paper>)}
      </Stack>}

      {tab === 3 && <Stack spacing={2}>
        <Button sx={{ alignSelf: 'flex-start' }} variant="contained" startIcon={<Add />} onClick={() => setDialog('field')}>שדה משתמש חדש</Button>
        {fields.length === 0 ? <Paper sx={{ p: 5, textAlign: 'center' }}>קטלוג שדות המשתמש ריק</Paper> : fields.map((field) => <Paper key={field.id} variant="outlined" sx={{ p: 2 }}><Stack direction="row" spacing={2} alignItems="center"><Person color="primary" /><Box flex={1}><Typography fontWeight={700}>{field.label_he}</Typography><Typography variant="body2" color="text.secondary">{field.key} · {field.field_type}</Typography></Box><Chip label={field.is_required ? 'חובה' : 'רשות'} /></Stack></Paper>)}
      </Stack>}
    </Stack>

    <Dialog open={dialog !== null} onClose={() => setDialog(null)} fullWidth maxWidth={dialog === 'role' ? 'md' : 'sm'}>
      <DialogTitle>{dialog === 'user' ? 'יצירת משתמש' : dialog === 'group' ? 'יצירת קבוצה' : dialog === 'role' ? 'יצירת תפקיד' : 'יצירת שדה משתמש'}</DialogTitle>
      <DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
        {dialog === 'user' && <>
          <TextField label="שם מלא" required value={userForm.display_name} onChange={(event) => setUserForm({ ...userForm, display_name: event.target.value })} />
          <TextField label="מייל" type="email" required value={userForm.email} onChange={(event) => setUserForm({ ...userForm, email: event.target.value })} />
          <TextField label="סיסמה זמנית" type="password" required value={userForm.password} onChange={(event) => setUserForm({ ...userForm, password: event.target.value })} />
          <FormControlLabel control={<Checkbox checked={userForm.is_active} onChange={(event) => setUserForm({ ...userForm, is_active: event.target.checked })} />} label="משתמש פעיל" />
          <FormControlLabel control={<Checkbox checked={userForm.is_system_admin} onChange={(event) => setUserForm({ ...userForm, is_system_admin: event.target.checked })} />} label="System Administrator" />
        </>}
        {dialog === 'group' && <><TextField label="שם הקבוצה" required value={groupForm.name} onChange={(event) => setGroupForm({ ...groupForm, name: event.target.value })} /><TextField label="תיאור" multiline value={groupForm.description} onChange={(event) => setGroupForm({ ...groupForm, description: event.target.value })} /></>}
        {dialog === 'role' && <>
          <TextField label="קוד Role" required value={roleForm.code} onChange={(event) => setRoleForm({ ...roleForm, code: event.target.value })} />
          <TextField label="שם התפקיד" required value={roleForm.name} onChange={(event) => setRoleForm({ ...roleForm, name: event.target.value })} />
          <TextField label="תיאור" value={roleForm.description} onChange={(event) => setRoleForm({ ...roleForm, description: event.target.value })} />
          <TextField select label="תחום" value={roleForm.scope} onChange={(event) => setRoleForm({ ...roleForm, scope: event.target.value })}><MenuItem value="environment">סביבתי</MenuItem><MenuItem value="system">מערכתי</MenuItem></TextField>
          <Typography fontWeight={700}>מטריצת Permissions</Typography>
          <Box sx={{ maxHeight: 300, overflow: 'auto', display: 'grid', gridTemplateColumns: { sm: '1fr 1fr' } }}>{permissionCatalog.map((permission) => <FormControlLabel key={permission.code} control={<Checkbox checked={roleForm.permissions.includes(permission.code)} onChange={(event) => setRoleForm({ ...roleForm, permissions: event.target.checked ? [...roleForm.permissions, permission.code] : roleForm.permissions.filter((code) => code !== permission.code) })} />} label={permission.code} />)}</Box>
        </>}
        {dialog === 'field' && <>
          <TextField label="מפתח" required value={fieldForm.key} onChange={(event) => setFieldForm({ ...fieldForm, key: event.target.value })} />
          <TextField label="תווית בעברית" required value={fieldForm.label_he} onChange={(event) => setFieldForm({ ...fieldForm, label_he: event.target.value })} />
          <TextField label="תווית באנגלית" required value={fieldForm.label_en} onChange={(event) => setFieldForm({ ...fieldForm, label_en: event.target.value })} />
          <TextField select label="סוג שדה" value={fieldForm.field_type} onChange={(event) => setFieldForm({ ...fieldForm, field_type: event.target.value })}>{['short_text','long_text','number','date','boolean','single_select','multi_select','user','email','phone'].map((type) => <MenuItem key={type} value={type}>{type}</MenuItem>)}</TextField>
          <FormControlLabel control={<Checkbox checked={fieldForm.is_required} onChange={(event) => setFieldForm({ ...fieldForm, is_required: event.target.checked })} />} label="חובה" />
        </>}
      </Stack></DialogContent>
      <DialogActions><Button onClick={() => setDialog(null)}>ביטול</Button><Button variant="contained" disabled={save.isPending} onClick={() => save.mutate()}>{save.isPending ? 'שומר...' : 'שמירה'}</Button></DialogActions>
    </Dialog>
  </Container>;
}
