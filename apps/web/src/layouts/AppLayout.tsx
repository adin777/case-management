import { type ReactNode, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Approval, Assessment, Dashboard, Groups, LockPerson, Logout, Menu, Notifications, Settings, SwitchAccount } from '@mui/icons-material';
import { Alert, AppBar, Avatar, Badge, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, MenuItem, TextField, Toolbar, Tooltip, Typography } from '@mui/material';
import { api, token } from '../api/client';
import type { User } from '../types';

type LinkItem = { url: string; label: string; icon: ReactNode; admin?: boolean };
const baseLinks: LinkItem[] = [
  { url: '/', label: 'ראשי', icon: <Dashboard/> },
  { url: '/reports/cases', label: 'דוח קריאות שירות', icon: <Assessment/> },
  { url: '/admin/environments', label: 'סביבות וסוגי קריאות', icon: <Settings/> },
  { url: '/admin/users', label: 'משתמשים והרשאות', icon: <Groups/>, admin: true },
  { url: '/admin/user-fields', label: 'הגדרות מערכת — שדות משתמש', icon: <Settings/>, admin: true },
  { url: '/admin/permissions', label: 'ניהול הרשאות גורף', icon: <LockPerson/>, admin: true },
];

export function AppLayout() {
  const navigate = useNavigate(); const routeLocation = useLocation(); const [open, setOpen] = useState(false); const [impersonationOpen, setImpersonationOpen] = useState(false); const [targetId, setTargetId] = useState('');
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const { data: impersonation } = useQuery({ queryKey: ['impersonation-status'], queryFn: () => api<{ active: boolean; can_start: boolean; impersonated_user_name?: string }>('/impersonation/status') });
  const { data: users = [] } = useQuery({ queryKey: ['users-for-impersonation'], queryFn: () => api<User[]>('/users'), enabled: !!impersonation?.can_start });
  const { data: approvals = [] } = useQuery({ queryKey: ['pending-approvals'], queryFn: () => api<unknown[]>('/approvals/pending-for-me') });
  const links: LinkItem[] = approvals.length ? [...baseLinks.slice(0, 2), { url: '/approvals/pending', label: 'קריאות ממתינות לאישור', icon: <Badge badgeContent={approvals.length} color="warning"><Approval/></Badge> }, ...baseLinks.slice(2)] : baseLinks;
  const visibleLinks = links.filter((link) => !link.admin || user?.is_system_admin);
  const drawer = <Box sx={{ width: 260 }}><Box className="drawer-brand">◆ מרכז השירות</Box><Divider/><List>{visibleLinks.map((link) => <ListItemButton selected={routeLocation.pathname === link.url} key={link.url} onClick={() => { navigate(link.url); setOpen(false); }}><ListItemIcon>{link.icon}</ListItemIcon><ListItemText primary={link.label}/></ListItemButton>)}</List></Box>;
  return <Box sx={{ display: 'flex' }}>
    <AppBar position="fixed" color="inherit" elevation={0} sx={{ borderBottom: '1px solid #e1e7f0', width: { md: 'calc(100% - 260px)' }, backdropFilter: 'blur(12px)', bgcolor: 'rgba(255,255,255,.92)' }}><Toolbar><IconButton aria-label="פתיחת תפריט" sx={{ display: { md: 'none' } }} onClick={() => setOpen(true)}><Menu/></IconButton><Box sx={{ flex: 1 }}/>{impersonation?.can_start && <Tooltip title="התחזות למשתמש"><IconButton onClick={() => setImpersonationOpen(true)}><SwitchAccount/></IconButton></Tooltip>}<Tooltip title="התראות"><IconButton aria-label="התראות"><Notifications/></IconButton></Tooltip><Avatar>{user?.display_name?.[0]}</Avatar><Typography sx={{ mx: 1 }}>{user?.display_name}</Typography><Tooltip title="יציאה"><IconButton aria-label="יציאה" onClick={() => { token.clear(); location.href = '/login'; }}><Logout/></IconButton></Tooltip></Toolbar></AppBar>
    <Drawer variant="permanent" anchor="right" sx={{ display: { xs: 'none', md: 'block' }, '& .MuiDrawer-paper': { width: 260 } }}>{drawer}</Drawer>
    <Drawer open={open} anchor="right" onClose={() => setOpen(false)} sx={{ display: { md: 'none' } }}>{drawer}</Drawer>
    <Box component="main" sx={{ flex: 1, p: { xs: 2, md: 4 }, mt: 8, mr: { md: '260px' }, minWidth: 0 }}>{impersonation?.active && <Alert severity="warning" sx={{ mb: 2 }} action={<Button color="inherit" onClick={async () => { const result = await api<{access_token:string}>('/impersonation/stop', { method: 'POST' }); token.setAccess(result.access_token); location.href = '/'; }}>חזרה למשתמש שלי</Button>}>אתה צופה במערכת כ־{impersonation.impersonated_user_name}</Alert>}<Outlet/></Box>
    <Dialog open={impersonationOpen} onClose={() => setImpersonationOpen(false)} fullWidth maxWidth="sm"><DialogTitle>התחזות למשתמש</DialogTitle><DialogContent><Alert severity="info" sx={{ mb: 2 }}>כל פעולה תירשם ב־Audit עם המשתמש המקורי והמשתמש המוצג.</Alert><TextField select fullWidth label="בחירת משתמש פעיל" value={targetId} onChange={(event) => setTargetId(event.target.value)}>{users.filter((row) => row.is_active !== false && row.id !== user?.id).map((row) => <MenuItem key={row.id} value={row.id}>{row.display_name} · {row.email}</MenuItem>)}</TextField></DialogContent><DialogActions><Button onClick={() => setImpersonationOpen(false)}>ביטול</Button><Button variant="contained" disabled={!targetId} onClick={async () => { const result = await api<{access_token:string}>('/impersonation/start', { method: 'POST', body: JSON.stringify({ user_id: targetId }) }); token.setAccess(result.access_token); location.href = '/'; }}>התחלת התחזות</Button></DialogActions></Dialog>
  </Box>;
}
