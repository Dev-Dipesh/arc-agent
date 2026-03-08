import { HumanInterrupt } from "@langchain/langgraph/prebuilt";

export function isAgentInboxInterruptSchema(
  value: unknown,
): value is HumanInterrupt | HumanInterrupt[] {
  const valueAsObject = Array.isArray(value) ? value[0] : value;
  return (
    valueAsObject &&
    typeof valueAsObject === "object" &&
    "action_request" in valueAsObject &&
    typeof valueAsObject.action_request === "object" &&
    "config" in valueAsObject &&
    typeof valueAsObject.config === "object" &&
    "allow_respond" in valueAsObject.config &&
    "allow_accept" in valueAsObject.config &&
    "allow_edit" in valueAsObject.config &&
    "allow_ignore" in valueAsObject.config
  );
}

export function isTokenLimitInterruptSchema(
  value: unknown,
): value is { type: "token_limit_warning"; token_count: number } {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const v = value as Record<string, unknown>;
  return v.type === "token_limit_warning" && typeof v.token_count === "number";
}

export function isMiddlewareHitlInterruptSchema(
  value: unknown,
): value is {
  action_requests: Array<{ name: string; args?: Record<string, unknown> }>;
  review_configs: Array<{ action_name: string; allowed_decisions: string[] }>;
} {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const v = value as Record<string, unknown>;
  return Array.isArray(v.action_requests) && Array.isArray(v.review_configs);
}
