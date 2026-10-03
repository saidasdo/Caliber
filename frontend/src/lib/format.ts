// SPEC section 8 copy rules: "226 k USD", "1.58 M USD"; dates "8 Apr 2026".

export function formatMoneyKusd(kusd: number): string {
  if (Math.abs(kusd) >= 1000) {
    return `${(kusd / 1000).toFixed(2)} M USD`;
  }
  return `${Math.round(kusd)} k USD`;
}

export function formatHours(hours: number): string {
  return `${hours.toFixed(1)} h`;
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}
