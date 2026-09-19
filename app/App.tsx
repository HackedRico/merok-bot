import { StatusBar } from 'expo-status-bar';
import { SafeAreaView } from 'react-native';
import { Chat } from './src/screens/Chat';
import { colors } from './src/theme';

export default function App() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.ground }}>
      <Chat />
      <StatusBar style="light" />
    </SafeAreaView>
  );
}
