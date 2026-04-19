interface Range {
  start: string | null;
  end: string | null;
}

export function averageHoursBetween(ranges: Range[]): number {
  const durations = ranges
    .filter((range) => range.start && range.end)
    .map((range) => {
      const start = new Date(range.start as string).getTime();
      const end = new Date(range.end as string).getTime();

      return (end - start) / (1000 * 60 * 60);
    })
    .filter((hours) => Number.isFinite(hours) && hours >= 0);

  if (durations.length === 0) {
    return 0;
  }

  const total = durations.reduce((sum, value) => sum + value, 0);

  return total / durations.length;
}
