import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AttachFile, DescriptionOutlined, Download } from '@mui/icons-material';
import { Box, Button, IconButton, Stack, Typography } from '@mui/material';
import { api, apiDownload, apiUpload } from '../../../api/client';
import type { Attachment } from '../../../types';
import { CaseSection } from './CaseSection';

export function CaseAttachments({ caseId }: { caseId: string }) {
  const client = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const { data: items = [] } = useQuery({ queryKey: ['attachments', caseId], queryFn: () => api<Attachment[]>(`/cases/${caseId}/attachments`), retry: false });
  const upload = async (file?: File) => { if (!file) return; setUploading(true); const form = new FormData(); form.append('file', file); await apiUpload(`/cases/${caseId}/attachments`, form); setUploading(false); client.invalidateQueries({ queryKey: ['attachments', caseId] }); };
  const download = async (item: Attachment) => { const blob = await apiDownload(`/attachments/${item.id}/download`); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = item.original_file_name; anchor.click(); URL.revokeObjectURL(url); };
  return <CaseSection title="קבצים מצורפים" icon={<AttachFile/>} action={<Button component="label" size="small" variant="outlined" disabled={uploading}>{uploading ? 'מעלה…' : 'העלאה'}<input hidden type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={(event) => upload(event.target.files?.[0])}/></Button>}><Stack spacing={1.25}>{items.map((item) => <Stack key={item.id} direction="row" alignItems="center" gap={1.25} sx={{ p: 1.25, borderRadius: 2.5, bgcolor: '#f8fafc' }}><Box sx={{ width: 38, height: 38, display: 'grid', placeItems: 'center', borderRadius: 2, bgcolor: '#e8efff', color: 'primary.main' }}><DescriptionOutlined/></Box><Box flex={1} minWidth={0}><Typography fontWeight={700} noWrap>{item.original_file_name}</Typography><Typography variant="caption" color="text.secondary">{Math.ceil(item.size_bytes / 1024)} KB · {new Date(item.uploaded_at).toLocaleDateString('he-IL')}</Typography></Box><IconButton aria-label="הורדה" onClick={() => download(item)}><Download/></IconButton></Stack>)}{!items.length && <Typography color="text.secondary">אין קבצים מצורפים</Typography>}</Stack></CaseSection>;
}
