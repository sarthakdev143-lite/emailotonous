import axios from "axios";

import type { AgentStatus, CreateThreadPayload, ThreadDetail, ThreadSummary } from "../types";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  timeout: 10_000,
});

export async function fetchStatus(): Promise<AgentStatus> {
  const response = await apiClient.get<AgentStatus>("/status");
  return response.data;
}

export async function fetchThreads(): Promise<ThreadSummary[]> {
  const response = await apiClient.get<ThreadSummary[]>("/threads");
  return response.data;
}

export async function fetchThread(threadId: string): Promise<ThreadDetail> {
  const response = await apiClient.get<ThreadDetail>(`/threads/${threadId}`);
  return response.data;
}

export async function createThread(payload: CreateThreadPayload): Promise<ThreadDetail> {
  const response = await apiClient.post<ThreadDetail>("/threads", payload);
  return response.data;
}

export async function triggerThread(threadId: string): Promise<ThreadDetail> {
  const response = await apiClient.post<ThreadDetail>(`/agent/trigger/${threadId}`);
  return response.data;
}

export async function processPuterResponse(
  threadId: string,
  llmResponse: string,
): Promise<ThreadDetail> {
  const response = await apiClient.post<ThreadDetail>("/agent/process-puter", {
    thread_id: threadId,
    llm_response: llmResponse,
  });
  return response.data;
}
