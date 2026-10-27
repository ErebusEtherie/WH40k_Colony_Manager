// Chronometer module for formatting a colony's age.
//
// The engine tracks colony age purely as elapsed "standard solar days"
// (colony.founding_days). No in-game calendar date / turn (year & quarter)
// is maintained anywhere — this module only converts those days into a
// human-readable years / months / days summary for display.

/**
 * Format a colony's age (in standard solar days) as readable text.
 *
 * @param foundingDays - Number of days since the colony was founded.
 * @returns The formatted string plus decomposed years / months / days parts.
 */
export const formatFoundingAge = (
  foundingDays: number
): {
  formatted: string;
  years: number;
  months: number;
  days: number;
} => {
  const years = Math.floor(foundingDays / 365);
  const remainingDays = foundingDays % 365;
  const months = Math.floor(remainingDays / 30);
  const days = remainingDays % 30;

  const parts: string[] = [];
  if (years > 0) parts.push(`${years}y`);
  if (months > 0) parts.push(`${months}m`);
  if (days > 0) parts.push(`${days}d`);

  return {
    formatted: parts.length > 0 ? parts.join(" ") : "0d",
    years,
    months,
    days,
  };
};
