export type NotificationTemplate = {
  id: string;
  label: string;
  subject: string;
  body: string;
};

export const NOTIFICATION_TEMPLATES: NotificationTemplate[] = [
  {
    id: "raw-marks",
    label: "Request for Raw Mark Sheets",
    subject: "Request for Raw Mark Sheets — [Semester / Course Name]",
    body: `Dear [Faculty Name],

This is a reminder to please submit the raw mark sheets for [Course Code / Semester] at your earliest convenience. These are required for the CO-PO attainment process.

Kindly upload them to the portal or send them to the department office by [Deadline Date].

Thank you.`,
  },
  {
    id: "copo-attainment",
    label: "Request for CO-PO Attainment Data",
    subject: "CO-PO Attainment Data Submission — [Academic Year]",
    body: `Dear [Faculty Name],

We require the CO-PO attainment data for your courses for the academic year [Year]. Please log in to the portal and complete the attainment generation for all your assigned courses.

Deadline: [Date]

Please reach out if you need any assistance.`,
  },
  {
    id: "signature",
    label: "Request for Signature on Document",
    subject: "Signature Required — [Document Name]",
    body: `Dear [Faculty Name],

Kindly review and sign the attached document: [Document Name]. This is required for [Purpose / Context].

Please return the signed copy to [Contact / Office] by [Date].

Thank you for your prompt attention.`,
  },
  {
    id: "profile-update",
    label: "Profile / Publication Update Reminder",
    subject: "Reminder to Update Your Faculty Profile",
    body: `Dear [Faculty Name],

This is a gentle reminder to update your faculty profile on the portal, including any recent publications, awards, funded projects, or professional achievements.

Keeping your profile current ensures accurate departmental reports and accreditation data.

Please complete your updates by [Date].`,
  },
  {
    id: "deadline",
    label: "Upcoming Deadline Reminder",
    subject: "Upcoming Deadline — [Task / Submission Name]",
    body: `Dear [Faculty Name],

This is a reminder that the deadline for [Task Description] is approaching on [Date]. Please ensure that all required submissions are completed on time through the portal.

Contact the admin office if you have any questions.`,
  },
  {
    id: "nba-accreditation",
    label: "NBA / Accreditation Data Request",
    subject: "Data Submission Required for NBA/Accreditation",
    body: `Dear [Faculty Name],

As part of our ongoing NBA/Accreditation preparation, we require the following data from you: [List of required items].

Please submit this through the portal or directly to the department office by [Deadline].

Your timely cooperation is highly appreciated.`,
  },
];

/** Highlight bracket placeholders in the compose preview. */
export function highlightPlaceholders(text: string): string {
  return text.replace(/\[([^\]]+)\]/g, "⟦$1⟧");
}
