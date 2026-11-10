function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function DocumentAnswerEvidence({ result }: { result: unknown }) {
  const value = record(result);
  const claims = Array.isArray(value.claims) ? value.claims : [];
  return (
    <section aria-label="Document answer and citations">
      <p>
        <strong>
          Document answer: {text(value.status).replaceAll("_", " ")}
        </strong>
        {text(value.as_of) && ` · Policy date ${text(value.as_of)}`}
      </p>
      {value.status === "failed" && (
        <p>
          {value.error_code === "reranker_dependency_missing"
            ? "Document lookup could not start because the server is missing local reranker dependencies. Ask an administrator to install the backend rerank dependency group, then retry this run. Teacher verification is required until it succeeds."
            : "Document lookup could not be completed. Teacher verification is required."}
        </p>
      )}
      {text(value.answer) && (
        <p style={{ whiteSpace: "pre-wrap" }}>{text(value.answer)}</p>
      )}
      {claims.map((raw, index) => {
        const claim = record(raw);
        const citations = Array.isArray(claim.citations) ? claim.citations : [];
        return (
          <div key={index}>
            <p>{text(claim.text)}</p>
            {citations.map((rawCitation, citationIndex) => {
              const citation = record(rawCitation);
              return (
                <div key={citationIndex}>
                  <p>
                    <strong>{text(citation.title)}</strong>
                    {` · Revision ${Number(citation.revision)} · Characters ${Number(citation.start)}–${Number(citation.end)}`}
                  </p>
                  <blockquote style={{ whiteSpace: "pre-wrap" }}>
                    {text(citation.quote)}
                  </blockquote>
                  <p className="muted">
                    {`[${text(citation.evidence_id)}] · Document ${text(citation.document_id)}`}
                    {text(citation.effective_from) &&
                      ` · From ${text(citation.effective_from)}`}
                    {text(citation.effective_to) &&
                      ` · Through ${text(citation.effective_to)}`}
                  </p>
                </div>
              );
            })}
          </div>
        );
      })}
      {Array.isArray(value.missing_information) &&
        value.missing_information.length > 0 && (
          <p>Unresolved: {value.missing_information.map(text).join("; ")}</p>
        )}
    </section>
  );
}
