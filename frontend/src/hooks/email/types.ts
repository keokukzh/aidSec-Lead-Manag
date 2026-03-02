export interface EmailTemplateItem {
  id: number;
  name: string;
  betreff: string;
  inhalt: string;
  kategorie?: string;
  is_ab_test: boolean;
  version: number;
  variables?: Record<string, unknown>;
  created_at: string;
}

export interface SequenceStepItem {
  day_offset: number;
  template_id?: number;
  subject_override?: string;
  body_override?: string;
}

export interface SequenceStepPreviewItem {
  stepIndex: number;
  dayOffset: number;
  templateName: string;
  subject: string;
  plain: string;
}

export interface SequenceScheduleItem {
  stepIndex: number;
  dayOffset: number;
  effectiveOffset: number;
  scheduledDateLabel: string;
  templateName: string;
}

export interface SequenceTimelineExport {
  exported_at: string;
  sequence_id: number | null;
  sequence_name: string;
  sequence_beschreibung: string;
  schedule_mode: "from-start" | "cumulative";
  start_date: string;
  steps: SequenceStepItem[];
  timeline: SequenceScheduleItem[];
}
