import { describe, expect, it } from 'vitest';
import { visibleConversationChannels } from './conversationChannels';

describe('visibleConversationChannels', () => {
  it('does not disclose the manager channel without read permission', () => {
    expect(visibleConversationChannels(false)).toEqual(['public']);
  });
  it('shows a separate manager channel to authorized managers', () => {
    expect(visibleConversationChannels(true)).toEqual(['public', 'manager']);
  });
});
