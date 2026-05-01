import { useEffect, useState } from "react";

import { fetchStatus } from "../api/client";
import type { AgentStatus } from "../types";

export interface UseAgentStatusResult {
  status: AgentStatus | null;
  loading: boolean;
  error: string | null;
  refetchStatus: () => Promise<void>;
}

export function useAgentStatus(): UseAgentStatusResult {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetchStatus = async (): Promise<void> => {
    setError(null);
    try {
      const nextStatus = await fetchStatus();
      setStatus(nextStatus);
    } catch (requestError) {
      setError("Couldn't reach the backend status endpoint.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refetchStatus();
    const intervalId = window.setInterval(() => {
      void refetchStatus();
    }, 30_000);
    return () => window.clearInterval(intervalId);
  }, []);

  return { status, loading, error, refetchStatus };
}
