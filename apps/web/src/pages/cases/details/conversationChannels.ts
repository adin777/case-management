export type ConversationChannel = 'public' | 'manager';

export function visibleConversationChannels(canReadManagerComments: boolean): ConversationChannel[] {
  return canReadManagerComments ? ['public', 'manager'] : ['public'];
}
