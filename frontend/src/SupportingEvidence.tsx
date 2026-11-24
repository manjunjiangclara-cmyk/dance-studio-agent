const clothingPolicyPrefix = "Beginner clothing policy, revision 1:";

function evidenceInfo(entry: string) {
  if (entry.startsWith("Class availability: "))
    return {
      label: "Class availability",
      summary: entry.slice("Class availability: ".length),
      source: "fact",
    };
  if (entry.startsWith("Alex's original email asks"))
    return {
      label: "Email context",
      summary:
        "Alex's latest email changes the preferred day from Thursday to Saturday.",
      source: "email",
    };
  if (entry.startsWith("The fictional absence notice"))
    return {
      label: "Absence notice",
      summary: "The absence notice arrived before the missed class began.",
      source: "fact",
    };
  if (entry.startsWith("Alex has recorded Level 2 attendance"))
    return {
      label: "Attendance & policy",
      summary:
        "The example policy allows a Level 2 replacement when the notice is timely.",
      source: "fact",
    };
  if (entry.startsWith("Saturday 13 February 2027, 6 pm"))
    return {
      label: "Class availability",
      summary:
        "The Saturday Level 2 class has one place available in this example.",
      source: "fact",
    };
  if (entry.startsWith("# Absences and makeup classes"))
    return {
      label: "Absences and makeup classes",
      summary: "Studio guidance on absence notices and makeup classes.",
      source: "fact",
    };
  if (
    /^[^\n]+ previously wrote:/.test(entry) ||
    entry.startsWith("Earlier email,")
  )
    return { label: "Student conversation", summary: entry, source: "fact" };
  if (
    /^(?:A new enquirer|[^\n]+ has (?:a recorded|recorded|no recorded))/.test(
      entry,
    )
  )
    return { label: "Student record", summary: entry, source: "fact" };
  if (entry.startsWith(clothingPolicyPrefix))
    return {
      label: "Studio policy",
      summary:
        "Comfortable clothes and socks are suitable; ballet shoes are optional.",
      source: "policy",
      document: {
        title: "Beginner clothing policy · Revision 1",
        text: entry.slice(clothingPolicyPrefix.length).trim(),
      },
    };
  if (entry.startsWith("No trial fee is specified"))
    return {
      label: "Missing fee information",
      summary: "The fictional policy does not specify the trial fee.",
      source: "policy",
    };
  return { label: "Supporting information", summary: entry, source: "fact" };
}

export function SupportingEvidence({
  evidence,
  showConversationLink = false,
}: {
  evidence: string[];
  showConversationLink?: boolean;
}) {
  return (
    <div className="live-draft-evidence">
      <h3>Supporting evidence</h3>
      <ul className="live-evidence-list">
        {evidence.map((entry, i) => {
          const info = evidenceInfo(entry);
          return (
            <li className="live-evidence-card" key={`${i}-${entry}`}>
              <div className="live-evidence-card-heading">
                <span className="live-evidence-number" aria-hidden="true">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <strong>{info.label}</strong>
              </div>
              <p>{info.summary}</p>
              <details className="live-evidence-detail">
                <summary>View source</summary>
                <div className="live-evidence-original">
                  <strong>
                    {info.document?.title || "Fictional demo input"}
                  </strong>
                  <p>{info.document?.text || entry}</p>
                  {info.source === "email" && showConversationLink && (
                    <a href="#conversation-heading">
                      View original student emails ↑
                    </a>
                  )}
                </div>
              </details>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
