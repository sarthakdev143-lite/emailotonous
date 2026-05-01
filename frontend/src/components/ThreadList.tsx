import type { ThreadSummary } from "../types";
import StatusBadge from "./StatusBadge";

interface ThreadListProps {
  threads: ThreadSummary[];
  selectedThreadId: string | null;
  loading: boolean;
  error: string | null;
  onSelectThread: (threadId: string) => void;
}

function formatUpdatedAt(timestamp: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

export default function ThreadList({
  threads,
  selectedThreadId,
  loading,
  error,
  onSelectThread,
}: ThreadListProps) {
  if (loading) {
    return <div className="rounded-[24px] border border-dashed border-stroke p-5 text-sm text-mist">Loading threads...</div>;
  }

  if (error) {
    return <div className="rounded-[24px] border border-rose/60 bg-rose/45 p-5 text-sm text-ink">{error}</div>;
  }

  if (threads.length === 0) {
    return (
      <div className="rounded-[24px] border border-dashed border-stroke p-5 text-sm text-mist">
        No threads yet. Create one from the panel above to send your first outreach.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {threads.map((thread) => {
        const selected = thread.id === selectedThreadId;
        return (
          <button
            key={thread.id}
            type="button"
            onClick={() => onSelectThread(thread.id)}
            className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${
              selected
                ? "border-brand bg-brandSoft/70 shadow-panel"
                : "border-stroke bg-panel hover:border-brand/35 hover:bg-canvas"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-semibold text-ink">
                  {thread.prospect_name ?? thread.prospect_email}
                </p>
                <p className="mt-1 text-xs uppercase tracking-[0.16em] text-mist">
                  {thread.prospect_email}
                </p>
              </div>
              <StatusBadge label={thread.status} />
            </div>
            <p className="mt-3 line-clamp-2 text-sm leading-6 text-mist">
              {thread.last_message_preview ?? thread.config.gig_description}
            </p>
            <p className="mt-3 text-xs text-mist">Updated {formatUpdatedAt(thread.updated_at)}</p>
          </button>
        );
      })}
    </div>
  );
}
