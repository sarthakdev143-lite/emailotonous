export interface AgentStatus {
  healthy: boolean;
  llm_available: boolean;
  llm_provider: string;
}

export interface ThreadConfig {
  gig_description: string;
  budget_ceiling: number;
  tone: string;
  available_slots: string[];
}

export interface MessageRecord {
  id: string;
  direction: "inbound" | "outbound";
  subject: string | null;
  body: string;
  email_message_id: string | null;
  intent: string | null;
  timestamp: string;
}

export interface BookingRecord {
  id: string;
  slot: string;
  status: string;
  cal_event_id: string | null;
  created_at: string;
}

export interface ThreadSummary {
  id: string;
  prospect_email: string;
  prospect_name: string | null;
  status: string;
  config: ThreadConfig;
  created_at: string;
  updated_at: string;
  last_message_preview: string | null;
}

export interface ThreadDetail extends ThreadSummary {
  messages: MessageRecord[];
  bookings: BookingRecord[];
}

export interface CreateThreadPayload {
  prospect_email: string;
  prospect_name: string;
  config: ThreadConfig;
}

export interface PuterChatClient {
  chat(prompt: string): Promise<string>;
}

export interface PuterGlobal {
  ai: PuterChatClient;
}

declare global {
  interface Window {
    puter?: PuterGlobal;
  }
}
