// AI Video Decompose - 类型定义

export interface Report {
  generated_at: string;
  source_video: string;
  title: string;
  duration_seconds: number;
  duration_label: string;
  hashtags: string[];
  script: Script;
  voice: Voice;
  chapters: Chapter[];
  scenes: Scene[];
  aligned: Aligned[];
  keyframe_mode: string;
}

export interface Script {
  total_chars: number;
  segment_count: number;
  avg_chars_per_segment: number;
  full_text: string;
  segments: Segment[];
}

export interface Segment {
  index: number;
  start: number;
  end: number;
  text: string;
  chars: number;
  time_range: string;
  role_guess: string;
}

export interface Voice {
  pitch_hz_median: number;
  gender_guess: string;
  energy_mean: number;
  speech_seconds: number;
  speech_ratio: number;
  chars_per_minute: number;
  likely_ai_tts: boolean;
  note: string;
}

export interface Chapter {
  index: number;
  start: number;
  end: number;
  time_range: string;
  duration_seconds: number;
  chars: number;
  role: string;
  title: string;
  summary: string;
  text: string;
}

export interface Scene {
  index: number;
  start: number;
  end: number;
  frame_path: string;
  visual_type: string;
  visual_hint: string;
  text: string;
  speech_index: number;
  time_range: string;
  duration_seconds: number;
  speech_text: string;
}

export interface Aligned {
  index: number;
  start: number;
  end: number;
  time_range: string;
  duration_seconds: number;
  chars: number;
  role: string;
  title: string;
  summary: string;
  text: string;
  scene_count: number;
  visual_types: string[];
  visual_summary: string;
  keyframes: string[];
}
