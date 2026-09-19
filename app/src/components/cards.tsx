import { Platform, Pressable, Text, View, Linking } from 'react-native';
import { Attachment, clipUrl } from '../api';
import { colors, mono } from '../theme';
import { Sparkline } from './Sparkline';

// One card per attachment kind the API returns. Every button sends a chat message through `onSend`,
// so a click and a typed sentence do exactly the same thing.

type Send = (message: string) => void;

export function Card({ attachment, onSend }: { attachment: Attachment; onSend: Send }) {
  switch (attachment.kind) {
    case 'templates':
      return <TemplatesCard templates={attachment.data.templates} onSend={onSend} />;
    case 'explanation':
      return <ExplanationCard e={attachment.data} />;
    case 'candidates':
      return <CandidatesCard data={attachment.data} onSend={onSend} />;
    case 'forecast':
      return <ForecastCard forecast={attachment.data.forecast} text={attachment.data.text} />;
    case 'clip':
      return <ClipCard clip={attachment.data} />;
    case 'post':
      return <PostCard data={attachment.data} onSend={onSend} />;
    case 'comparison':
      return <ComparisonCard c={attachment.data} />;
    default:
      return null;
  }
}

const s = {
  card: { backgroundColor: colors.panel, borderColor: colors.rule, borderWidth: 1, borderRadius: 8, padding: 12, marginTop: 8, gap: 8 } as const,
  title: { color: colors.muted, fontFamily: mono, fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' as const },
  body: { color: colors.ink, fontSize: 14, lineHeight: 20 },
  dim: { color: colors.muted, fontSize: 13, lineHeight: 18 },
  row: { flexDirection: 'row' as const, alignItems: 'center' as const, gap: 8, flexWrap: 'wrap' as const },
  chip: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999, borderWidth: 1, fontSize: 11, fontFamily: mono },
  button: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6, backgroundColor: colors.panelRaised, borderWidth: 1, borderColor: colors.rule },
  buttonText: { color: colors.ink, fontSize: 12, fontFamily: mono },
  num: { color: colors.ink, fontFamily: mono, fontSize: 13 },
};

function Chip({ label, tone }: { label: string; tone: 'good' | 'bad' | 'muted' }) {
  const color = tone === 'good' ? colors.good : tone === 'bad' ? colors.bad : colors.muted;
  return <Text style={[s.chip, { color, borderColor: color }]}>{label}</Text>;
}

function Button({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={s.button}>
      <Text style={s.buttonText}>{label}</Text>
    </Pressable>
  );
}

function TemplatesCard({ templates, onSend }: { templates: any[]; onSend: Send }) {
  return (
    <View style={s.card}>
      <Text style={s.title}>Spreading now · distinct authors per hour</Text>
      {templates.slice(0, 10).map((t, i) => (
        <View key={i} style={{ gap: 4, borderTopWidth: i ? 1 : 0, borderTopColor: colors.rule, paddingTop: i ? 8 : 0 }}>
          <Text style={s.body} numberOfLines={2}>{t.text}</Text>
          <View style={s.row}>
            <Text style={s.num}>{t.authors} accounts · {t.posts} posts</Text>
            <Chip label={t.spam.is_spam ? 'paid' : 'organic'} tone={t.spam.is_spam ? 'bad' : 'good'} />
            <Sparkline points={t.curve} valueKey="authors" color={t.spam.is_spam ? colors.bad : colors.accent} />
            <Button label="explain" onPress={() => onSend(`What is this: "${t.text}"`)} />
          </View>
          <Text style={s.dim}>{t.spam.reasons.join(' · ')}</Text>
        </View>
      ))}
    </View>
  );
}

function ExplanationCard({ e }: { e: any }) {
  const t = e.template;
  return (
    <View style={s.card}>
      <Text style={s.title}>Explain · similarity {(e.similarity * 100).toFixed(0)}%</Text>
      {t ? (
        <>
          <Text style={s.body}>"{t.text}"</Text>
          <View style={s.row}>
            <Text style={s.num}>{t.authors} accounts · first seen {String(t.first_seen).slice(0, 16).replace('T', ' ')} UTC</Text>
            <Chip label={t.spam.is_spam ? 'paid' : 'organic'} tone={t.spam.is_spam ? 'bad' : 'good'} />
            <Sparkline points={t.curve} valueKey="authors" />
          </View>
          <Text style={s.dim}>{t.spam.reasons.join(' · ')}</Text>
        </>
      ) : (
        <Text style={s.dim}>No template in the current window matched.</Text>
      )}
      <Text style={s.body}>{e.gloss}</Text>
    </View>
  );
}

function CandidatesCard({ data, onSend }: { data: any; onSend: Send }) {
  const { candidates, forecasts, baseline } = data;
  return (
    <View style={s.card}>
      <Text style={s.title}>Five drafts · median {Math.round(baseline.median_likes)} likes over {baseline.posts} posts</Text>
      {candidates.map((c: any, i: number) => {
        const f = forecasts[i];
        const top = f?.drivers?.[0];
        return (
          <View key={i} style={{ gap: 6, borderTopWidth: i ? 1 : 0, borderTopColor: colors.rule, paddingTop: i ? 8 : 0 }}>
            <Text style={s.body}>
              <Text style={{ color: colors.accent, fontFamily: mono }}>{i + 1}  </Text>
              {c.text}
            </Text>
            {f && (
              <Text style={s.dim}>
                ~{Math.round(f.likes_1d)} likes in a day · {f.relative_to_median.toFixed(1)}x median
                {f.likes_1h != null ? ` · ~${Math.round(f.likes_1h)} in the first hour` : ''}
                {top ? ` · ${top.detail} (${top.effect > 0 ? '+' : ''}${top.effect.toFixed(2)})` : ''}
              </Text>
            )}
            {c.rationale ? <Text style={s.dim}>why: {c.rationale}</Text> : null}
            <View style={s.row}>
              <Button label="score" onPress={() => onSend(`score draft ${i + 1}`)} />
              <Button label="clip" onPress={() => onSend(`turn draft ${i + 1} into a clip`)} />
              <Button label="post" onPress={() => onSend(`post draft ${i + 1}`)} />
            </View>
          </View>
        );
      })}
    </View>
  );
}

function ForecastCard({ forecast, text }: { forecast: any; text: string }) {
  const max = Math.max(0.01, ...forecast.drivers.map((d: any) => Math.abs(d.effect)));
  return (
    <View style={s.card}>
      <Text style={s.title}>Forecast</Text>
      <Text style={s.dim} numberOfLines={2}>{text}</Text>
      <Text style={s.body}>
        ~{Math.round(forecast.likes_1d)} likes in a day · {forecast.relative_to_median.toFixed(1)}x the median
        {forecast.likes_1h != null ? ` · ~${Math.round(forecast.likes_1h)} in the first hour` : ''}
      </Text>
      {forecast.drivers.map((d: any, i: number) => (
        <View key={i} style={s.row}>
          <View style={{ width: 120 * (Math.abs(d.effect) / max), height: 8, backgroundColor: d.effect > 0 ? colors.good : colors.bad, borderRadius: 2 }} />
          <Text style={s.dim}>{d.detail} ({d.effect > 0 ? '+' : ''}{d.effect.toFixed(2)} log-likes)</Text>
        </View>
      ))}
    </View>
  );
}

function ClipCard({ clip }: { clip: any }) {
  const url = clipUrl(clip.path);
  return (
    <View style={s.card}>
      <Text style={s.title}>Clip · {clip.duration_s.toFixed(0)}s · voice {clip.voice_used} · background {clip.visuals_used}</Text>
      {Platform.OS === 'web' ? (
        // On web the clip plays inline; native gets expo-video in Part 2.
        <video src={url} controls playsInline style={{ width: 240, height: 427, borderRadius: 8, backgroundColor: '#000' }} />
      ) : (
        <Button label="open clip" onPress={() => Linking.openURL(url)} />
      )}
      <Text style={s.dim}>{clip.captions.map((c: any) => c.text).join(' / ')}</Text>
      {clip.sound ? <Text style={s.dim}>sound to add at upload: {clip.sound.title}</Text> : null}
    </View>
  );
}

function PostCard({ data, onSend }: { data: any; onSend: Send }) {
  return (
    <View style={s.card}>
      <Text style={s.title}>Posted · {data.post.platform} · {data.post.id}</Text>
      <Text style={s.body}>{data.text}</Text>
      <View style={s.row}>
        <Button label="how did it do?" onPress={() => onSend('How did it do?')} />
      </View>
    </View>
  );
}

function ComparisonCard({ c }: { c: any }) {
  const points = c.curve.points;
  const span = points.length ? points[points.length - 1].minutes / 60 : 0;
  return (
    <View style={s.card}>
      <Text style={s.title}>Learn · {points.length} observations over {span.toFixed(0)} hours</Text>
      <View style={s.row}>
        <Sparkline points={points} valueKey="likes" height={48} />
        <Text style={s.body}>{c.likes_at_30} likes vs {Math.round(c.predicted_at_30)} forecast</Text>
      </View>
      <Chip label={c.verdict} tone={c.verdict.startsWith('ahead') ? 'good' : c.verdict.startsWith('behind') ? 'bad' : 'muted'} />
    </View>
  );
}
