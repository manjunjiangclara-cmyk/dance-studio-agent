import type { Location, Session, StudioClass } from "./types";

export interface ConfirmedSession {
  session: Session;
  regularClass: StudioClass;
  location: Location;
}

export function confirmedSessions({
  studentId,
  sessions,
  classes,
  locations,
}: {
  studentId: string;
  sessions: Session[];
  classes: StudioClass[];
  locations: Location[];
}): ConfirmedSession[] {
  const classById = new Map(classes.map((row) => [row.id, row]));
  const locationById = new Map(locations.map((row) => [row.id, row]));
  return sessions
    .flatMap((session) => {
      if (!session.students.includes(studentId)) return [];
      const regularClass = classById.get(session.class_id);
      const location =
        regularClass && locationById.get(regularClass.location_id);
      return regularClass && location
        ? [{ session, regularClass, location }]
        : [];
    })
    .sort(
      (a, b) =>
        new Date(a.session.starts_at).getTime() -
          new Date(b.session.starts_at).getTime() ||
        a.session.id.localeCompare(b.session.id),
    );
}
