export function StudentMemorySections({
  context,
  summary,
}: {
  context: Record<string, unknown>;
  summary: string | null;
}) {
  const memory = context._agent_memory;
  const record =
    memory && typeof memory === "object" && !Array.isArray(memory)
      ? (memory as Record<string, unknown>)
      : {};
  const requestMap =
    record.requests &&
    typeof record.requests === "object" &&
    !Array.isArray(record.requests)
      ? Object.values(record.requests)
      : [];
  const requests = requestMap.flatMap((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return [];
    const entry = item as Record<string, unknown>;
    return typeof entry.request_summary === "string" &&
      entry.request_summary.trim()
      ? [
          {
            text: entry.request_summary,
            kind: entry.kind,
            approved: typeof entry.approved_response_id === "string",
          },
        ]
      : [];
  });
  if (
    !requests.length &&
    typeof record.request_summary === "string" &&
    record.request_summary.trim()
  )
    requests.push({
      text: record.request_summary,
      kind: undefined,
      approved: false,
    });
  const preferenceMap =
    record.preferences &&
    typeof record.preferences === "object" &&
    !Array.isArray(record.preferences)
      ? Object.values(record.preferences)
      : [];
  const preferences = preferenceMap.flatMap((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return [];
    const value = (item as Record<string, unknown>).value;
    return typeof value === "string" && value.trim() ? [value] : [];
  });
  const hasStructuredRequests = requestMap.length > 0;
  const generatedSummary = summary?.startsWith(
    "Conversational memory; official student records remain authoritative.",
  );
  const requestsByConversation =
    record.requests &&
    typeof record.requests === "object" &&
    !Array.isArray(record.requests)
      ? (record.requests as Record<string, unknown>)
      : {};
  const approvedResponses =
    record.approved_responses &&
    typeof record.approved_responses === "object" &&
    !Array.isArray(record.approved_responses)
      ? Object.entries(record.approved_responses)
      : [];
  const earlierResponses = approvedResponses.flatMap(([id, item]) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return [];
    const entry = item as Record<string, unknown>;
    const current =
      typeof entry.conversation_id === "string"
        ? requestsByConversation[entry.conversation_id]
        : undefined;
    const currentId =
      current && typeof current === "object" && !Array.isArray(current)
        ? (current as Record<string, unknown>).source_message_id
        : undefined;
    return currentId !== id &&
      typeof entry.request_summary === "string" &&
      entry.request_summary.trim()
      ? [entry.request_summary]
      : [];
  });
  return (
    <div className="profile-memory-content">
      <div className="profile-memory-activity">
        <span>Conversation summary</span>
        {hasStructuredRequests && generatedSummary ? (
          <p>
            {preferences.length
              ? preferences.join(" ")
              : "No ongoing preferences recorded yet."}
          </p>
        ) : (
          <p>{summary || "No conversation summary yet."}</p>
        )}
      </div>
      <div className="profile-memory-activity profile-request-summary">
        <span>Request summary</span>
        {requests.length ? (
          requests.map((request, index) => (
            <p key={index}>
              {request.text}
              {request.kind === "teacher_reviewed" ? " (Teacher reviewed)" : ""}
              {request.approved
                ? " Response approved; delivery unconfirmed."
                : ""}
            </p>
          ))
        ) : (
          <p>No requests recorded yet.</p>
        )}
      </div>
      {earlierResponses.length > 0 && (
        <div className="profile-memory-activity profile-request-summary">
          <span>Earlier teacher-approved responses</span>
          {earlierResponses.map((response, index) => (
            <p key={index}>{response} Delivery unconfirmed.</p>
          ))}
        </div>
      )}
      {hasStructuredRequests && generatedSummary && summary && (
        <details className="profile-full-summary">
          <summary>View full stored summary</summary>
          <p>{summary}</p>
        </details>
      )}
    </div>
  );
}
