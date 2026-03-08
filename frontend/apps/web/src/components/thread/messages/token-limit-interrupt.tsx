"use client";

import { useStreamContext } from "@/providers/Stream";
import { Button } from "@/components/ui/button";
import { useQueryState } from "nuqs";
import { useState } from "react";
import { toast } from "sonner";

export function TokenLimitInterruptView({
  interrupt,
}: {
  interrupt: { type: "token_limit_warning"; token_count: number };
}) {
  const thread = useStreamContext();
  const [, setThreadId] = useQueryState("threadId");
  const [submitting, setSubmitting] = useState(false);

  const handleSummarize = () => {
    try {
      setSubmitting(true);
      thread.submit(
        {},
        { command: { resume: { action: "summarize" } } },
      );
    } catch {
      toast.error("Failed to resume.");
      setSubmitting(false);
    }
  };

  const handleNewChat = () => {
    setThreadId(null);
  };

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-background">
      <div className="bg-muted px-4 py-2 border-b border-border">
        <h3 className="font-medium text-foreground">Context Limit Approaching</h3>
      </div>
      <div className="p-4 space-y-3">
        <p className="text-sm text-muted-foreground">
          This conversation has reached{" "}
          <span className="font-medium text-foreground">
            ~{Math.round(interrupt.token_count / 1000)}k tokens
          </span>
          . How would you like to proceed?
        </p>
        <div className="space-y-2">
          <div className="rounded border border-border p-3 bg-muted/50">
            <p className="text-sm font-medium text-foreground">Start a new chat</p>
            <p className="text-xs text-muted-foreground mt-1">
              Clean slate with full accuracy. Recommended for operations that need
              precise tab or space IDs.
            </p>
          </div>
          <div className="rounded border border-border p-3 bg-muted/50">
            <p className="text-sm font-medium text-foreground">Summarize and continue</p>
            <p className="text-xs text-muted-foreground mt-1">
              Compresses history to free up space. May lose exact identifiers — the agent
              could hallucinate tab IDs or miss earlier context.
            </p>
          </div>
        </div>
        <div className="flex gap-2 pt-1">
          <Button size="sm" onClick={handleNewChat}>
            Start New Chat
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleSummarize}
            disabled={submitting}
          >
            Summarize and Continue
          </Button>
        </div>
      </div>
    </div>
  );
}
