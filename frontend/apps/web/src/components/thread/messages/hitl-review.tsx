import { useState } from "react";
import { useStreamContext } from "@/providers/Stream";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

type ActionRequest = {
  name: string;
  args?: Record<string, unknown>;
  description?: string;
};

type ReviewConfig = {
  action_name: string;
  allowed_decisions: string[];
};

export function MiddlewareHitlReviewView({
  interrupt,
}: {
  interrupt: {
    action_requests: ActionRequest[];
    review_configs: ReviewConfig[];
  };
}) {
  const thread = useStreamContext();
  const [submitting, setSubmitting] = useState(false);

  const submitDecision = (decision: "approve" | "reject") => {
    try {
      setSubmitting(true);
      const decisions = interrupt.action_requests.map((req, idx) => {
        const cfg = interrupt.review_configs[idx];
        const allowed = cfg?.allowed_decisions ?? [];
        const finalDecision = allowed.includes(decision)
          ? decision
          : (allowed[0] ?? "reject");
        return {
          type: finalDecision,
          ...(finalDecision === "edit"
            ? { edited_action: { name: req.name, args: req.args ?? {} } }
            : {}),
        };
      });

      thread.submit(
        {},
        {
          command: {
            resume: { decisions },
          },
        },
      );
    } catch (e) {
      console.error("Failed to submit HITL decision", e);
      toast.error("Failed to submit approval decision.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
        <h3 className="font-medium text-gray-900">Approval Required</h3>
      </div>
      <div className="p-3 space-y-3">
        {interrupt.action_requests.map((req, idx) => (
          <div key={`${req.name}-${idx}`} className="rounded border p-3">
            <div className="text-sm font-medium">{req.name}</div>
            {req.description ? (
              <div className="text-xs text-muted-foreground mt-1">
                {req.description}
              </div>
            ) : null}
          </div>
        ))}
        <div className="flex gap-2">
          <Button
            onClick={() => submitDecision("approve")}
            disabled={submitting}
            size="sm"
          >
            Approve
          </Button>
          <Button
            onClick={() => submitDecision("reject")}
            disabled={submitting}
            size="sm"
            variant="destructive"
          >
            Reject
          </Button>
        </div>
      </div>
    </div>
  );
}
