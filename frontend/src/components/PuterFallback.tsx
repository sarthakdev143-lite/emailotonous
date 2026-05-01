import { useEffect, useState } from "react";

import { processPuterResponse } from "../api/client";
import type { ThreadDetail } from "../types";

interface PuterFallbackProps {
  thread: ThreadDetail;
  onThreadUpdated: (thread: ThreadDetail) => void;
}

function buildPuterPrompt(thread: ThreadDetail): string {
  const history = thread.messages.length
    ? thread.messages.map((message) => `${message.direction.toUpperCase()}: ${message.body}`).join("\n")
    : "No prior thread history.";

  return [
    "You are a sharp, warm talent acquisition specialist.",
    `You are emailing ${thread.prospect_name ?? thread.prospect_email} about this gig: ${thread.config.gig_description}.`,
    "",
    "Your only goal is to get them on a call.",
    `Maximum budget: ${thread.config.budget_ceiling}.`,
    `Tone: ${thread.config.tone}.`,
    `Available slots: ${thread.config.available_slots.join(", ")}.`,
    "",
    "Pick exactly one JSON tool call object using one of these shapes:",
    '{"name":"send_email","subject":"string","body":"string"}',
    '{"name":"propose_calendar_slot","body":"string","slots":["ISO datetime"]}',
    '{"name":"walk_away","body":"string"}',
    '{"name":"reschedule","body":"string","cancelled_slot":"ISO datetime","new_slots":["ISO datetime"]}',
    "",
    "Conversation history:",
    history,
    "",
    "Return JSON only.",
  ].join("\n");
}

export default function PuterFallback({
  thread,
  onThreadUpdated,
}: PuterFallbackProps) {
  const [scriptReady, setScriptReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (window.puter !== undefined) {
      setScriptReady(true);
      return;
    }

    const existingScript = document.querySelector<HTMLScriptElement>('script[data-puter-script="true"]');
    if (existingScript !== null) {
      existingScript.addEventListener("load", () => setScriptReady(true), { once: true });
      existingScript.addEventListener("error", () => setError("Puter.js failed to load."), { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://js.puter.com/v2/";
    script.async = true;
    script.dataset.puterScript = "true";
    script.onload = () => setScriptReady(true);
    script.onerror = () => setError("Puter.js failed to load.");
    document.body.appendChild(script);
  }, []);

  const handleGenerate = async (): Promise<void> => {
    if (window.puter?.ai === undefined) {
      setError("Puter.js is still loading.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const prompt = buildPuterPrompt(thread);
      const llmResponse = await window.puter.ai.chat(prompt);
      const updatedThread = await processPuterResponse(thread.id, llmResponse);
      onThreadUpdated(updatedThread);
    } catch (requestError) {
      setError("Puter.js couldn't finish the agent turn.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-[24px] border border-brand/20 bg-brandSoft/60 p-5">
      <p className="text-xs uppercase tracking-[0.18em] text-brand">Running on Puter.js (free mode)</p>
      <p className="mt-3 text-sm leading-6 text-ink">
        No server-side LLM key is configured, so this thread can still move forward through the browser.
      </p>
      <button
        type="button"
        disabled={!scriptReady || loading}
        onClick={() => {
          void handleGenerate();
        }}
        className="mt-4 rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:bg-stroke disabled:text-mist"
      >
        {loading ? "Generating..." : "Generate next move"}
      </button>
      {error !== null ? <p className="mt-3 text-sm text-ink">{error}</p> : null}
    </div>
  );
}
