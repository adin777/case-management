import { renderToStaticMarkup } from 'react-dom/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import { describe, expect, it } from 'vitest';
import i18n from '../i18n';
import { NotificationBell } from './notifications/NotificationBell';
import { ModuleDirectory } from './ModuleDirectory';
import { ScreenHeader } from './ScreenHeader';

describe('accessible shared controls', () => {
  it('renders the bell as a single native keyboard-operable button', () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(['notifications', 'bell'], { items: [], unread: 3 });
    const html = renderToStaticMarkup(<I18nextProvider i18n={i18n}><QueryClientProvider client={client}><MemoryRouter><NotificationBell /></MemoryRouter></QueryClientProvider></I18nextProvider>);
    expect(html).toMatch(/<button[^>]*aria-label="[^"]+"[^>]*aria-haspopup="dialog"[^>]*aria-expanded="false"/);
    expect(html.match(/<button\b/g)).toHaveLength(1);
    expect(html).toContain('>3</span>');
    client.clear();
  });
  it('renders the screen title at heading level one without changing the action', () => {
    const html = renderToStaticMarkup(<ScreenHeader title="Requests" subtitle="Find your work" action={<a href="/cases/new">Create</a>} />);
    expect(html).toMatch(/<h1[^>]*>Requests<\/h1>/);
    expect(html).toContain('href="/cases/new"');
  });
  it('keeps every configuration/report destination a labelled native button', () => {
    const html = renderToStaticMarkup(<I18nextProvider i18n={i18n}><ModuleDirectory items={[
      { id: 'a', title: 'Reports', description: 'Case reporting', icon: null, onOpen: () => undefined },
      { id: 'b', title: 'Permissions', description: 'Manage access', icon: null, onOpen: () => undefined },
    ]} /></I18nextProvider>);
    expect(html.match(/<button\b/g)).toHaveLength(2);
    expect(html).toMatch(/<h2[^>]*>Reports<\/h2>/);
    expect(html).toMatch(/<h2[^>]*>Permissions<\/h2>/);
  });
});
