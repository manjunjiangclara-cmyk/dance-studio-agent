import { CalendarDays, MapPin, Check, Clock } from "lucide-react";
import { Link } from "react-router-dom";
import "./booking-proposal.css";
export function BookingProposal({
  booked,
  className,
  startsAt,
  timezone = "Australia/Melbourne",
  location,
  sessionUrl,
}: {
  booked: boolean;
  className: string;
  startsAt?: string;
  timezone?: string;
  location?: string;
  sessionUrl?: string;
}) {
  const date = startsAt
    ? new Intl.DateTimeFormat("en-AU", {
        dateStyle: "full",
        timeZone: timezone,
      }).format(new Date(startsAt))
    : "Session unavailable";
  const time = startsAt
    ? new Intl.DateTimeFormat("en-AU", {
        hour: "numeric",
        minute: "2-digit",
        timeZone: timezone,
      }).format(new Date(startsAt))
    : "Time unavailable";
  return (
    <section
      className={`booking-proposal ${booked ? "booking-proposal-confirmed" : ""}`}
      aria-labelledby="booking-proposal-heading"
    >
      <header>
        <h3 id="booking-proposal-heading">
          {booked ? "Booking confirmed" : "Proposed class booking"}
        </h3>
        <span className="booking-proposal-badge">
          {booked ? <Check size={14} /> : <Clock size={14} />}{" "}
          {booked ? "Confirmed" : "Awaiting approval"}
        </span>
      </header>
      <h4 className="booking-proposal-class">{className}</h4>
      <dl className="booking-proposal-facts">
        <div>
          <dt>
            <CalendarDays size={15} /> Date
          </dt>
          <dd>{date}</dd>
        </div>
        <div>
          <dt>
            <Clock size={15} /> Time
          </dt>
          <dd>
            {time}
            <small>{timezone}</small>
          </dd>
        </div>
        <div>
          <dt>
            <MapPin size={15} /> Location
          </dt>
          <dd>{location || "Location unavailable"}</dd>
        </div>
      </dl>
      {!booked && (
        <div className="booking-proposal-note">
          <strong>No place reserved yet</strong>
          <p>
            Approval books this exact session after a fresh capacity check. Ask
            for a revision to change the session.
          </p>
        </div>
      )}
      {sessionUrl && (
        <Link className="inline-link" to={sessionUrl}>
          View session students
        </Link>
      )}
    </section>
  );
}
