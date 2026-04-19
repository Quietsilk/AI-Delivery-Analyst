export interface DeliveryMetrics {
  cycleTimeHours: number;
  leadTimeHours: number;
  throughput: number;
  predictability: number;
  backlogSize: number;
  inProgressCount: number;
  completedCount: number;
}
