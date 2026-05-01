import { startTransition, useEffect, useState } from "react";

import { createThread, fetchThread, fetchThreads, triggerThread } from "./api/client";
import PuterFallback from "./components/PuterFallback";
import ThreadDetail from "./components/ThreadDetail";
import ThreadList from "./components/ThreadList";
import { useAgentStatus } from "./hooks/useAgentStatus";
import type { CreateThreadPayload, ThreadDetail as ThreadDetailRecord, ThreadSummary } from "./types";

interface ThreadFormState {
  prospectEmail: string;
  prospectName: string;
  gigDescription: string;
  budgetCeiling: string;
  tone: string;
  availableSlots: string;
}

const INITIAL_FORM_STATE: ThreadFormState = {
  prospectEmail: "",
  prospectName: "",
  gigDescription: "",
  budgetCeiling: "5000",
  tone: "warm, concise, and direct",
  availableSlots: "2026-05-05T10:00:00+05:30\n2026-05-05T14:00:00+05:30\n2026-05-06T11:00:00+05:30",
};

function buildCreatePayload(formState: ThreadFormState): CreateThreadPayload {
  return {
    prospect_email: formState.prospectEmail.trim(),
    prospect_name: formState.prospectName.trim(),
    config: {
      gig_description: formState.gigDescription.trim(),
      budget_ceiling: Number(formState.budgetCeiling),
      tone: formState.tone.trim(),
      available_slots: formState.availableSlots
        .split("\n")
        .map((slot) => slot.trim())
        .filter((slot) => slot.length > 0),
    },
  };
}

export default function App() {
  const { status, loading: statusLoading, error: statusError, refetchStatus } = useAgentStatus();
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(true);
  const [threadsError, setThreadsError] = useState<string | null>(null);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [selectedThread, setSelectedThread] = useState<ThreadDetailRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [formState, setFormState] = useState<ThreadFormState>(INITIAL_FORM_STATE);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  const refreshThreads = async (focusThreadId?: string | null): Promise<void> => {
    setThreadsError(null);
    try {
      const threadList = await fetchThreads();
      startTransition(() => {
        setThreads(threadList);
        setThreadsLoading(false);
        if (focusThreadId !== undefined && focusThreadId !== null) {
          setSelectedThreadId(focusThreadId);
        } else if (selectedThreadId === null && threadList.length > 0) {
          setSelectedThreadId(threadList[0].id);
        }
      });
    } catch (requestError) {
      setThreadsLoading(false);
      setThreadsError("Couldn't load threads from the backend.");
    }
  };

  useEffect(() => {
    void refreshThreads();
  }, []);

  useEffect(() => {
    if (selectedThreadId === null) {
      setSelectedThread(null);
      return;
    }

    const loadThread = async (): Promise<void> => {
      setDetailLoading(true);
      setDetailError(null);
      try {
        const detail = await fetchThread(selectedThreadId);
        startTransition(() => {
          setSelectedThread(detail);
          setDetailLoading(false);
        });
      } catch (requestError) {
        setDetailLoading(false);
        setDetailError("Couldn't load that thread.");
      }
    };

    void loadThread();
  }, [selectedThreadId]);

  const handleFormChange = (field: keyof ThreadFormState, value: string): void => {
    setFormState((currentState) => ({
      ...currentState,
      [field]: value,
    }));
  };

  const handleCreateThread = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setFormSubmitting(true);
    setFormError(null);
    try {
      const createdThread = await createThread(buildCreatePayload(formState));
      setFormState(INITIAL_FORM_STATE);
      startTransition(() => {
        setSelectedThread(createdThread);
        setSelectedThreadId(createdThread.id);
      });
      await refreshThreads(createdThread.id);
    } catch (requestError) {
      setFormError("Thread creation failed. Check the inputs and try again.");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleTriggerThread = async (): Promise<void> => {
    if (selectedThreadId === null) {
      return;
    }

    setTriggerLoading(true);
    setDetailError(null);
    try {
      const updatedThread = await triggerThread(selectedThreadId);
      startTransition(() => {
        setSelectedThread(updatedThread);
      });
      await refreshThreads(selectedThreadId);
    } catch (requestError) {
      setDetailError("The backend couldn't run a server-side agent turn for this thread.");
    } finally {
      setTriggerLoading(false);
    }
  };

  const handlePuterUpdate = (updatedThread: ThreadDetailRecord): void => {
    startTransition(() => {
      setSelectedThread(updatedThread);
    });
    void refreshThreads(updatedThread.id);
    void refetchStatus();
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-[1600px] flex-col px-4 py-6 lg:px-6">
      <section className="panel-frame mb-6 overflow-hidden">
        <div className="grid gap-4 px-6 py-5 lg:grid-cols-[minmax(0,1fr)_24rem] lg:items-center">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-mist">Autonomous outreach dashboard</p>
            <h1 className="mt-3 font-serif text-[2.4rem] font-semibold tracking-[-0.04em] text-ink">
              Email Wake-Up Agent
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-mist">
              Manage cold outreach, negotiation, reschedules, and booking flow from one thread-aware control room.
            </p>
          </div>

          <div className="rounded-[24px] border border-stroke bg-canvas p-5">
            <p className="text-xs uppercase tracking-[0.18em] text-mist">LLM status</p>
            <div className="mt-3 flex items-center gap-3">
              <span className="h-3 w-3 rounded-full bg-brand" />
              <p className="text-lg font-semibold text-ink">
                {statusLoading ? "Checking..." : status?.llm_provider ?? "unknown"}
              </p>
            </div>
            <p className="mt-2 text-sm text-mist">
              {status?.llm_available === false
                ? "Server-side keys are missing, so Puter.js will handle reasoning in the browser."
                : "Server-side reasoning is available for direct backend turns."}
            </p>
            {statusError !== null ? <p className="mt-3 text-sm text-ink">{statusError}</p> : null}
          </div>
        </div>
      </section>

      <section className="grid flex-1 gap-6 xl:grid-cols-[26rem_minmax(0,1fr)]">
        <aside className="space-y-6">
          <section className="panel-frame p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-mist">Trigger panel</p>
                <h2 className="mt-2 section-title text-[1.5rem]">Start a new thread</h2>
              </div>
              <span className="rounded-full bg-brandSoft px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-brand">
                Live
              </span>
            </div>

            <form className="mt-5 space-y-4" onSubmit={(event) => void handleCreateThread(event)}>
              <label className="block">
                <span className="text-xs uppercase tracking-[0.16em] text-mist">Prospect email</span>
                <input
                  type="email"
                  value={formState.prospectEmail}
                  onChange={(event) => handleFormChange("prospectEmail", event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-stroke bg-canvas px-4 py-3 text-sm text-ink outline-none transition focus:border-brand"
                  placeholder="prospect@example.com"
                  required
                />
              </label>

              <label className="block">
                <span className="text-xs uppercase tracking-[0.16em] text-mist">Prospect name</span>
                <input
                  type="text"
                  value={formState.prospectName}
                  onChange={(event) => handleFormChange("prospectName", event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-stroke bg-canvas px-4 py-3 text-sm text-ink outline-none transition focus:border-brand"
                  placeholder="Robin Recruit"
                />
              </label>

              <label className="block">
                <span className="text-xs uppercase tracking-[0.16em] text-mist">Gig description</span>
                <textarea
                  value={formState.gigDescription}
                  onChange={(event) => handleFormChange("gigDescription", event.target.value)}
                  className="mt-2 min-h-[8rem] w-full rounded-[24px] border border-stroke bg-canvas px-4 py-3 text-sm text-ink outline-none transition focus:border-brand"
                  placeholder="Three-week lifecycle sprint for a fintech product launch."
                  required
                />
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block">
                  <span className="text-xs uppercase tracking-[0.16em] text-mist">Budget ceiling</span>
                  <input
                    type="number"
                    min="0"
                    value={formState.budgetCeiling}
                    onChange={(event) => handleFormChange("budgetCeiling", event.target.value)}
                    className="mt-2 w-full rounded-2xl border border-stroke bg-canvas px-4 py-3 text-sm text-ink outline-none transition focus:border-brand"
                    required
                  />
                </label>

                <label className="block">
                  <span className="text-xs uppercase tracking-[0.16em] text-mist">Tone</span>
                  <input
                    type="text"
                    value={formState.tone}
                    onChange={(event) => handleFormChange("tone", event.target.value)}
                    className="mt-2 w-full rounded-2xl border border-stroke bg-canvas px-4 py-3 text-sm text-ink outline-none transition focus:border-brand"
                    required
                  />
                </label>
              </div>

              <label className="block">
                <span className="text-xs uppercase tracking-[0.16em] text-mist">Available slots (one ISO time per line)</span>
                <textarea
                  value={formState.availableSlots}
                  onChange={(event) => handleFormChange("availableSlots", event.target.value)}
                  className="mt-2 min-h-[7rem] w-full rounded-[24px] border border-stroke bg-canvas px-4 py-3 font-mono text-xs text-ink outline-none transition focus:border-brand"
                  required
                />
              </label>

              <button
                type="submit"
                disabled={formSubmitting}
                className="w-full rounded-full bg-brand px-5 py-3 text-sm font-semibold text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:bg-stroke disabled:text-mist"
              >
                {formSubmitting ? "Creating..." : "Create thread"}
              </button>
              {formError !== null ? <p className="text-sm text-ink">{formError}</p> : null}
            </form>
          </section>

          <section className="panel-frame p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-mist">Thread list</p>
                <h2 className="mt-2 section-title text-[1.4rem]">Live conversations</h2>
              </div>
            </div>
            <ThreadList
              threads={threads}
              selectedThreadId={selectedThreadId}
              loading={threadsLoading}
              error={threadsError}
              onSelectThread={setSelectedThreadId}
            />
          </section>
        </aside>

        <ThreadDetail
          thread={selectedThread}
          loading={detailLoading}
          error={detailError}
          onTriggerThread={handleTriggerThread}
          triggerDisabled={selectedThread === null || status?.llm_available === false}
          triggerLabel={status?.llm_available === false ? "Use Puter below" : "Trigger agent"}
          triggerLoading={triggerLoading}
          fallbackPanel={
            selectedThread !== null && status?.llm_available === false ? (
              <PuterFallback thread={selectedThread} onThreadUpdated={handlePuterUpdate} />
            ) : null
          }
        />
      </section>
    </main>
  );
}
