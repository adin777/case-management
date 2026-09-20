import { Notifications } from '@mui/icons-material';
import {
  Badge,
  IconButton,
  Button,
  List,
  ListItemButton,
  ListItemText,
  Popover,
  Stack,
  Typography,
  Tooltip,
} from '@mui/material';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { useTranslation } from 'react-i18next';

type Item = {
  id: string;
  title: string;
  body: string;
  route?: string;
  is_read: boolean;
  created_at: string;
};

type Result = { items: Item[]; unread: number };

export function NotificationBell() {
  const { t } = useTranslation();
  const [anchor, setAnchor] = useState<HTMLElement>();
  const navigate = useNavigate();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ['notifications', 'bell'],
    queryFn: () => api<Result>('/notifications?page=1&page_size=8'),
    refetchInterval: 30_000,
  });
  const refresh = () => client.invalidateQueries({ queryKey: ['notifications'] });
  const open = async (item: Item) => {
    if (!item.is_read) await api(`/notifications/${item.id}/read?is_read=true`, { method: 'PUT' });
    setAnchor(undefined);
    await refresh();
    navigate(item.route || '/notifications', {
      state: { returnTo: '/notifications', returnLabel: 'חזרה להתראות' },
    });
  };

  return <>
    <Tooltip title={t('header.notifications')}><IconButton aria-label={t('header.notifications')} aria-haspopup="dialog" aria-expanded={Boolean(anchor)} onClick={(event) => setAnchor(event.currentTarget)}>
      <Badge color="error" badgeContent={query.data?.unread || 0}><Notifications /></Badge>
    </IconButton></Tooltip>
    <Popover
      open={Boolean(anchor)}
      anchorEl={anchor}
      onClose={() => setAnchor(undefined)}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
    >
      <Stack sx={{ width: { xs: 'calc(100vw - 24px)', sm: 390 }, maxHeight: '70vh' }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" p={2}>
          <Typography fontWeight={650}>התראות</Typography>
          <Button size="small" onClick={async () => {
            await api('/notifications/read-all', { method: 'PUT' });
            await refresh();
          }}>סמן הכל כנקרא</Button>
        </Stack>
        <List sx={{ overflowY: 'auto' }}>
          {query.data?.items.map((item) => <ListItemButton
            key={item.id}
            onClick={() => open(item)}
            sx={{ bgcolor: item.is_read ? 'transparent' : 'action.hover' }}
          >
            <ListItemText
              primary={item.title}
              secondary={`${item.body} · ${new Date(item.created_at).toLocaleString('he-IL')}`}
            />
          </ListItemButton>)}
        </List>
        <Button onClick={() => { setAnchor(undefined); navigate('/notifications'); }}>כל ההתראות</Button>
      </Stack>
    </Popover>
  </>;
}
