export function StudentEmailCard({
  name,
  messages,
}: {
  name: string;
  messages: {
    body: string;
    time?: string;
    dateTime?: string;
    sender?: "teacher";
  }[];
}) {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .join("");
  return (
    <section className="panel" aria-labelledby="conversation-heading">
      <div className="live-conversation-heading">
        <div>
          <h2 id="conversation-heading">Student email</h2>
          <p>Conversation in the order received</p>
        </div>
        <span>
          {messages.length} {messages.length === 1 ? "message" : "messages"}
        </span>
      </div>
      <ol
        className="live-conversation"
        aria-label={
          messages.some((message) => message.sender === "teacher")
            ? "Student and teacher conversation"
            : "Student email conversation"
        }
      >
        {messages.map((message, index) => (
          <li
            className={`live-conversation-message${message.sender === "teacher" ? " live-conversation-reply" : ""}`}
            key={index}
          >
            <span className="live-conversation-avatar" aria-hidden="true">
              {message.sender === "teacher" ? "MB" : initials}
            </span>
            <div className="live-conversation-content">
              {message.sender === "teacher" && (
                <div className="live-conversation-sender">
                  Merri Ballet team · Accepted reply · simulated
                </div>
              )}
              {message.time && (
                <div className="live-conversation-sender">
                  <time dateTime={message.dateTime}>{message.time}</time>
                </div>
              )}
              <div className="live-conversation-bubble">{message.body}</div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
