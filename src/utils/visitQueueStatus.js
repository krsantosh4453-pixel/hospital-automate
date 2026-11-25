// BUG-011: a visit stays "Waiting" until the consultation starts, while its
// queue token moves through Called, Acknowledged and Ready. Show the queue's
// word for a waiting visit, so Consultation and the queue say the same thing.
const CALLED_STATES = ["Called", "Acknowledged", "Ready"]

export function visitStatusShown(visitStatus, queueStatus) {
  if (visitStatus === "Waiting" && CALLED_STATES.includes(queueStatus)) return queueStatus
  return visitStatus
}
