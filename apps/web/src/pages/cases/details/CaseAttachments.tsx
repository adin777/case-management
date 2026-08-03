import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AttachFile, Download } from '@mui/icons-material';
import { Button, Card, CardContent, Divider, Stack, Typography } from '@mui/material';
import { api, apiDownload, apiUpload } from '../../../api/client';
import type { Attachment } from '../../../types';

export function CaseAttachments({ caseId }: { caseId: string }) {
  const client = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const { data: items = [] } = useQuery({ queryKey: ['attachments', caseId], queryFn: () => api<Attachment[]>(`/cases/${caseId}/attachments`), retry: false });
  const upload = async (file?: File) => { if (!file) return; setUploading(true); const form = new FormData(); form.append('file', file); await apiUpload(`/cases/${caseId}/attachments`, form); setUploading(false); client.invalidateQueries({ queryKey: ['attachments', caseId] }); };
  const download = async (item: Attachment) => { const blob = await apiDownload(`/attachments/${item.id}/download`); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = item.original_file_name; anchor.click(); URL.revokeObjectURL(url); };
  return <Card variant="outlined"><CardContent><Typography variant="h6" fontWeight={800}>קבצים מצורפים</Typography><Divider sx={{ my: 1.5 }} /><Button component="label" startIcon={<AttachFile />} variant="outlined" disabled={uploading}>{uploading ? 'מעלה…' : 'בחירת קובץ'}<input hidden type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" capture="environment" onChange={(event) => upload(event.target.files?.[0])} /></Button><Stack spacing={1} mt={2}>{items.map((item) => <Stack key={item.id} direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1}><span><Typography fontWeight={700}>{item.original_file_name}</Typography><Typography variant="caption">{Math.ceil(item.size_bytes / 1024)} KB · {new Date(item.uploaded_at).toLocaleString('he-IL')}</Typography></span><Button startIcon={<Download />} onClick={() => download(item)}>הורדה</Button></Stack>)}{!items.length && <Typography color="text.secondary">אין קבצים מצורפים</Typography>}</Stack></CardContent></Card>;
}
