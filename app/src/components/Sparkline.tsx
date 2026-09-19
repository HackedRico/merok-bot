import { View } from 'react-native';
import { colors } from '../theme';

type Point = { hour?: string; minutes?: number; authors?: number; likes?: number };

// Bars, not a chart library: the curve is a handful of hourly counts and a View per bar reads fine on web and phone.
export function Sparkline({ points, valueKey, color = colors.accent, height = 34 }: { points: Point[]; valueKey: 'authors' | 'likes'; color?: string; height?: number }) {
  const values = points.map((p) => Number(p[valueKey] ?? 0));
  const max = Math.max(1, ...values);
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', height, gap: 2 }}>
      {values.map((v, i) => (
        <View key={i} style={{ width: 6, height: Math.max(2, (v / max) * height), backgroundColor: color, borderRadius: 1, opacity: 0.9 }} />
      ))}
    </View>
  );
}
