import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { Attachment, Health, health, sendMessage } from '../api';
import { Card } from '../components/cards';
import { colors, mono } from '../theme';

type Turn = { role: 'user' | 'assistant'; text: string; attachments?: Attachment[]; tool?: string };

const SUGGESTIONS = [
  'What are people posting this hour?',
  'What is this: "do you remember when you joined X? I do!"',
  "Help me announce Thursday's town hall.",
  'Post the best one',
  'Turn draft 1 into a clip',
  'How did it do?',
];

export function Chat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [cid, setCid] = useState<string | null>(null);
  const [status, setStatus] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scroll = useRef<ScrollView>(null);

  useEffect(() => {
    health().then(setStatus).catch((e) => setError(String(e)));
    // `?say=...` runs a message on load, so a demo link or a screenshot lands on a real card, not an empty chat.
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      const say = new URLSearchParams(window.location.search).get('say');
      if (say) setTimeout(() => send(say), 300);
    }
  }, []);

  useEffect(() => {
    scroll.current?.scrollToEnd({ animated: true });
  }, [turns, busy]);

  async function send(message: string) {
    const text = message.trim();
    if (!text || busy) return;
    setInput('');
    setError(null);
    setTurns((t) => [...t, { role: 'user', text }]);
    setBusy(true);
    try {
      const res = await sendMessage(text, cid);
      setCid(res.conversation_id);
      setTurns((t) => [...t, { role: 'assistant', text: res.reply.text, attachments: res.reply.attachments, tool: res.reply.tool_calls[0]?.tool }]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, backgroundColor: colors.ground }}>
      <View style={{ flex: 1, maxWidth: 860, width: '100%', alignSelf: 'center' }}>
        <Header status={status} />
        <ScrollView ref={scroll} style={{ flex: 1 }} contentContainerStyle={{ padding: 16, gap: 12 }}>
          {turns.length === 0 && (
            <Text style={{ color: colors.muted, fontSize: 15, lineHeight: 22 }}>
              Ask what is spreading, paste a post to explain, or say what you want to post. Every card's buttons send a message you could have typed.
            </Text>
          )}
          {turns.map((t, i) => (
            <View key={i} style={{ alignSelf: t.role === 'user' ? 'flex-end' : 'stretch', maxWidth: t.role === 'user' ? '80%' : '100%' }}>
              {t.role === 'user' ? (
                <Text style={{ color: colors.ink, backgroundColor: colors.user, padding: 10, borderRadius: 10, fontSize: 15 }}>{t.text}</Text>
              ) : (
                <View>
                  {t.tool && <Text style={{ color: colors.accent, fontFamily: mono, fontSize: 11, letterSpacing: 1, marginBottom: 4 }}>{t.tool.toUpperCase()}</Text>}
                  <Text style={{ color: colors.ink, fontSize: 15, lineHeight: 22 }}>{t.text}</Text>
                  {t.attachments?.map((a, j) => <Card key={j} attachment={a} onSend={send} />)}
                </View>
              )}
            </View>
          ))}
          {busy && <ActivityIndicator color={colors.accent} />}
          {error && <Text style={{ color: colors.bad, fontFamily: mono, fontSize: 12 }}>{error}</Text>}
        </ScrollView>
        <View style={{ padding: 12, gap: 8, borderTopWidth: 1, borderTopColor: colors.rule }}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
            {SUGGESTIONS.map((sugg) => (
              <Pressable key={sugg} onPress={() => send(sugg)} style={{ borderWidth: 1, borderColor: colors.rule, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5 }}>
                <Text style={{ color: colors.muted, fontSize: 12 }}>{sugg}</Text>
              </Pressable>
            ))}
          </ScrollView>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <TextInput
              value={input}
              onChangeText={setInput}
              onSubmitEditing={() => send(input)}
              placeholder="Say what you want to post, or paste something to explain"
              placeholderTextColor={colors.muted}
              style={{ flex: 1, color: colors.ink, backgroundColor: colors.panel, borderRadius: 8, padding: 12, fontSize: 15, borderWidth: 1, borderColor: colors.rule }}
              returnKeyType="send"
            />
            <Pressable onPress={() => send(input)} style={{ backgroundColor: colors.accent, borderRadius: 8, paddingHorizontal: 16, justifyContent: 'center' }}>
              <Text style={{ color: '#111', fontWeight: '600' }}>Send</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

function Header({ status }: { status: Health | null }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 14, paddingBottom: 8, borderBottomWidth: 1, borderBottomColor: colors.rule, flexWrap: 'wrap', gap: 8 }}>
      <Text style={{ color: colors.ink, fontSize: 22, fontWeight: '700' }}>merok-bot</Text>
      <Text style={{ color: colors.muted, fontFamily: mono, fontSize: 11 }}>
        {status
          ? `@${status.demo_handle} · ${status.rows.toLocaleString()} posts from ${status.data_source} · model ${status.llm_configured ? 'live' : 'offline'} · voice ${status.voice} · ${status.publisher}`
          : 'connecting to the API…'}
      </Text>
    </View>
  );
}
