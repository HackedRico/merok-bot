// The one client for the API. Types mirror shared/types.py after to_json().

export type ToolCall = { tool: string; args: Record<string, unknown> };
export type Attachment = { kind: string; data: Record<string, any> };
export type Reply = { text: string; tool_calls: ToolCall[]; attachments: Attachment[] };
export type ChatResponse = { conversation_id: string; reply: Reply };
export type Health = {
  status: string;
  data_source: string;
  rows: number;
  demo_handle: string;
  llm: string;
  llm_configured: boolean;
  voice: string;
  visuals: string;
  publisher: string;
  poller: string;
  baseline: { author: string; median_likes: number; posts: number };
};

export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export async function sendMessage(message: string, conversationId: string | null): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function health(): Promise<Health> {
  const res = await fetch(`${API_URL}/health`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export function clipUrl(path: string): string {
  const name = path.split('/').pop() ?? '';
  return `${API_URL}/clips/${name}`;
}
