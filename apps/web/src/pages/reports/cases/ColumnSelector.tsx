import { ViewColumn } from '@mui/icons-material';
import { Button, Checkbox, FormControlLabel, Menu, MenuItem } from '@mui/material';
import { useState } from 'react';
import type { CaseReportRow } from '../../../types';
import { reportColumns } from './reportColumns';

export function ColumnSelector({ value, onChange }: { value: (keyof CaseReportRow)[]; onChange: (value: (keyof CaseReportRow)[]) => void }) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  return <><Button startIcon={<ViewColumn />} onClick={(event) => setAnchor(event.currentTarget)}>בחירת עמודות</Button>
    <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
      {reportColumns.map(([key, label]) => <MenuItem key={key} dense><FormControlLabel label={label} control={<Checkbox checked={value.includes(key)} onChange={() => {
        const next = value.includes(key) ? value.filter((item) => item !== key) : [...value, key];
        if (next.length) onChange(next);
      }} />} /></MenuItem>)}
    </Menu></>;
}
