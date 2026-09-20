import { renderToStaticMarkup } from 'react-dom/server';
import { I18nextProvider } from 'react-i18next';
import { describe, expect, it } from 'vitest';
import i18n from '../../../i18n';
import { SortableFieldRow } from './SortableFieldRow';
import type { GlobalField } from './types';

describe('responsive global field records', () => {
  it('exposes labelled values, drag and management controls without a technical identifier', () => {
    const row: GlobalField = { id: 'field-1', key: 'global_internal_key', label_he: 'סיווג', label_en: 'Category', field_type: 'single_select', is_required: true, is_active: true, track_history: false, sort_order: 0, options: [{ id: 'option-1', label_he: 'ערך', label_en: 'Value', is_active: true, sort_order: 0 }] };
    const html = renderToStaticMarkup(<I18nextProvider i18n={i18n}><table><tbody><SortableFieldRow row={row} onMenu={() => undefined} onManageOptions={() => undefined} /></tbody></table></I18nextProvider>);
    expect(html).not.toContain('global_internal_key');
    expect(html.match(/data-label=/g)).toHaveLength(8);
    expect(html).toContain('record-title');
    expect(html).toContain('record-actions');
    expect(html).toContain('record-drag');
    expect(html).toContain('ניהול ערכים (1)');
    expect(html).toContain('פעולות: סיווג');
    expect(html).toContain('גרירת סיווג');
    expect(html).toContain('פעיל');
  });
});
