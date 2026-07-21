export type NotificationTemplate = {
  id: string;
  label: string;
  requirement_type: string;
  subject: string;
  body: string;
};

export const NOTIFICATION_TEMPLATES: NotificationTemplate[] = [
  {
    id: "course-upcoming-sem",
    label: "Upcoming Semester Course Details",
    requirement_type: "course_upcoming_sem",
    subject: "Upcoming Semester Course Details — [Semester]",
    body: `Dear [Faculty Name],

Please submit the course(s) you will teach in the upcoming semester, including course code, title, and any co-instructors.

Deadline: [Date]

Thank you.`,
  },
  {
    id: "yearly-report",
    label: "Yearly Report Submission",
    requirement_type: "yearly_report",
    subject: "Yearly Report Submission — [Academic Year]",
    body: `Dear [Faculty Name],

Please submit your yearly report for [Academic Year] at your earliest convenience.

Deadline: [Date]

Thank you.`,
  },
  {
    id: "new-awards",
    label: "New Awards Update",
    requirement_type: "new_awards",
    subject: "New Awards Update Request",
    body: `Dear [Faculty Name],

Please update the portal with any new awards or recognitions received since we last asked.

Deadline: [Date]

Thank you.`,
  },
  {
    id: "new-fdps",
    label: "New FDPs Update",
    requirement_type: "new_fdps",
    subject: "New FDPs / Training Update Request",
    body: `Dear [Faculty Name],

Please report any new FDPs, STTPs, or training programs you have attended since we last asked.

Deadline: [Date]

Thank you.`,
  },
  {
    id: "verify-sdgs",
    label: "Verify Project SDGs (Projects and Theses)",
    requirement_type: "verify_sdgs",
    subject: "Verify & Accept SDGs for Your Projects (Projects and Theses)",
    body: `Dear [Faculty Name],

Please log in to the Projects and Theses tab and verify & accept the SDGs linked to your student projects.

Deadline: [Date]

Thank you.`,
  },
  {
    id: "copo-attainment",
    label: "CO-PO Attainment Data",
    requirement_type: "copo_attainment",
    subject: "CO-PO Attainment Data — Previous Semester",
    body: `Dear [Faculty Name],

Please submit CO-PO attainment data for the course(s) you taught in the previous semester via the CO-PO Generator.

Deadline: [Date]

Thank you.`,
  },
];

export const REMINDER_QUICK_PICKS = [
  { label: "Off", minutes: 0 },
  { label: "1 day", minutes: 24 * 60 },
  { label: "2 days", minutes: 2 * 24 * 60 },
  { label: "3 days", minutes: 3 * 24 * 60 },
  { label: "1 week", minutes: 7 * 24 * 60 },
  { label: "2 weeks", minutes: 14 * 24 * 60 },
];

export const REMINDER_UNITS = [
  { value: "minutes", label: "minutes", multiplier: 1 },
  { value: "hours", label: "hours", multiplier: 60 },
  { value: "days", label: "days", multiplier: 24 * 60 },
  { value: "weeks", label: "weeks", multiplier: 7 * 24 * 60 },
] as const;

export const MAX_REMINDER_DAYS = 180;

export function minutesFromCustom(value: number, unit: (typeof REMINDER_UNITS)[number]["value"]): number {
  const mult = REMINDER_UNITS.find((u) => u.value === unit)?.multiplier ?? 1;
  return Math.round(value * mult);
}

export const REMINDER_INTERVALS = REMINDER_QUICK_PICKS;
