import { ReactNode, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Assignment, Dashboard, Groups, Logout, Menu, Notifications, Settings, TaskAlt } from '@mui/icons-material';
import { AppBar, Avatar, Box, Divider, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Tooltip, Typography } from '@mui/material';
import { api, token } from '../api/client';
import type { User } from '../types';

type LinkItem = { url: string; label: string; icon: ReactNode; admin?: boolean };
const links: LinkItem[] = [
  { url: '/', label: 'ראשי', icon: <Dashboard /> },
  { url: '/cases', label: 'הקריאות שלי', icon: <Assignment /> },
  { url: '/assigned', label: 'קריאות בטיפולי', icon: <TaskAlt /> },
  { url: '/admin/environments', label: 'סביבות וסוגי קריאות', icon: <Settings /> },
  { url: '/admin/users', label: 'משתמשים והרשאות', icon: <Groups />, admin: true },
];

export function AppLayout() {
  const navigate = useNavigate();
  const routeLocation = useLocation();
  const [open, setOpen] = useState(false);
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const visibleLinks = links.filter((link) => !link.admin || user?.is_system_admin);
  const drawer = <Box sx={{ width: 250 }}><Box className="drawer-brand">◆ מרכז השירות</Box><Divider /><List>{visibleLinks.map((link) => <ListItemButton selected={routeLocation.pathname === link.url} key={link.url} onClick={() => { navigate(link.url); setOpen(false); }}><ListItemIcon>{link.icon}</ListItemIcon><ListItemText primary={link.label} /></ListItemButton>)}</List></Box>;
  return <Box sx={{ display: 'flex' }}>
    <AppBar position="fixed" color="inherit" elevation={0} sx={{ borderBottom: '1px solid #e5eaf1', width: { md: 'calc(100% - 250px)' } }}><Toolbar><IconButton aria-label="פתיחת תפריט" sx={{ display: { md: 'none' } }} onClick={() => setOpen(true)}><Menu /></IconButton><Box sx={{ flex: 1 }} /><Tooltip title="התראות"><IconButton aria-label="התראות"><Notifications /></IconButton></Tooltip><Avatar>{user?.display_name?.[0]}</Avatar><Typography sx={{ mx: 1 }}>{user?.display_name}</Typography><Tooltip title="יציאה"><IconButton aria-label="יציאה" onClick={() => { token.clear(); location.href = '/login'; }}><Logout /></IconButton></Tooltip></Toolbar></AppBar>
    <Drawer variant="permanent" anchor="right" sx={{ display: { xs: 'none', md: 'block' }, '& .MuiDrawer-paper': { width: 250 } }}>{drawer}</Drawer>
    <Drawer open={open} anchor="right" onClose={() => setOpen(false)} sx={{ display: { md: 'none' } }}>{drawer}</Drawer>
    <Box component="main" sx={{ flex: 1, p: { xs: 2, md: 4 }, mt: 8, mr: { md: '250px' }, minWidth: 0 }}><Outlet /></Box>
  </Box>;
}
