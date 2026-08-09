import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AdminPanelSettings, ChatBubbleOutline, Send } from '@mui/icons-material';
import { Alert, Avatar, Box, Button, Card, CardContent, Paper, Stack, Tab, Tabs, TextField, Typography } from '@mui/material';
import { api } from '../../../api/client';
import type { CasePermissions, Comment, User } from '../../../types';
import { visibleConversationChannels, type ConversationChannel } from './conversationChannels';

function Feed({ rows, me, channel }: { rows: Comment[]; me?: User; channel: ConversationChannel }) {
  if (!rows.length) return <Box sx={{ py: 7, textAlign: 'center', color: 'text.secondary' }}>
    {channel === 'manager' ? 'עדיין אין הערות מנהל' : 'עדיין אין הודעות בשיחה'}
  </Box>;
  return <Stack spacing={1.5}>{rows.map((row) => <Box key={row.id} sx={{ display: 'flex', gap: 1, flexDirection: row.author_id === me?.id ? 'row-reverse' : 'row' }}>
    <Avatar sx={{ bgcolor: channel === 'manager' ? 'secondary.main' : 'primary.main' }}>{row.author_name?.[0] || 'מ'}</Avatar>
    <Paper variant="outlined" sx={{ p: 1.5, maxWidth: '84%', bgcolor: channel === 'manager' ? '#f0fdfa' : '#fff' }}>
      <Typography variant="caption" fontWeight={800}>{row.author_name || 'משתמש'}</Typography>
      <Typography sx={{ whiteSpace: 'pre-wrap' }}>{row.body}</Typography>
      <Typography variant="caption" color="text.secondary">{new Date(row.created_at).toLocaleString('he-IL')}</Typography>
    </Paper>
  </Box>)}</Stack>;
}

export function ConversationPanel({ caseId, permissions, me, onError }: { caseId: string; permissions: CasePermissions; me?: User; onError: (message: string) => void }) {
  const qc = useQueryClient();
  const channels = visibleConversationChannels(permissions.can_read_manager_comments);
  const [channel, setChannel] = useState<ConversationChannel>('public');
  const [body, setBody] = useState('');
  useEffect(() => { if (!channels.includes(channel)) setChannel('public'); }, [channel, channels]);
  const endpoint = channel === 'manager' ? 'manager-comments' : 'public-comments';
  const canWrite = channel === 'public' || permissions.can_create_manager_comments;
  const { data: rows = [], isLoading, isError } = useQuery({
    queryKey: [endpoint, caseId], queryFn: () => api<Comment[]>(`/cases/${caseId}/${endpoint}`),
  });
  const send = useMutation({
    mutationFn: () => api(`/cases/${caseId}/${endpoint}`, { method: 'POST', body: JSON.stringify({ body: body.trim() }) }),
    onSuccess: () => { setBody(''); qc.invalidateQueries({ queryKey: [endpoint, caseId] }); },
    onError: (error) => onError((error as Error).message),
  });
  return <Card><CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
    {channels.length > 1 ? <Tabs value={channel} onChange={(_, value) => { setChannel(value); setBody(''); }} variant="fullWidth" sx={{ mb: 2 }}>
      <Tab value="public" icon={<ChatBubbleOutline fontSize="small"/>} iconPosition="start" label="שיחה"/>
      <Tab value="manager" icon={<AdminPanelSettings fontSize="small"/>} iconPosition="start" label="הערות מנהל"/>
    </Tabs> : <Typography variant="h6" mb={2}>שיחה</Typography>}
    {channel === 'manager' && <Alert severity="info" sx={{ mb: 2 }}>ערוץ פנימי למנהלי מערכת וסביבה בלבד</Alert>}
    <Box aria-live="polite" sx={{ minHeight: 280, maxHeight: 540, overflowY: 'auto', px: .5 }}>
      {isLoading ? <Typography color="text.secondary" textAlign="center" py={7}>טוען הודעות…</Typography> : isError ? <Alert severity="error">לא ניתן לטעון את ההודעות</Alert> : <Feed rows={rows} me={me} channel={channel}/>} 
    </Box>
    {canWrite && <Stack spacing={1.25} mt={2} pt={2} sx={{ borderTop: '1px solid #e5eaf2' }}>
      <TextField fullWidth multiline minRows={3} label={channel === 'manager' ? 'כתיבת הערת מנהל' : 'כתיבת תגובה'} value={body} onChange={(event) => setBody(event.target.value)}/>
      <Button variant="contained" endIcon={<Send/>} disabled={!body.trim() || send.isPending} onClick={() => send.mutate()}>{send.isPending ? 'שולח…' : 'שליחה'}</Button>
    </Stack>}
  </CardContent></Card>;
}
