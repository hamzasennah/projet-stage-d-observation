export type Criterion = {
  label: string;
  weight: number;
  description: string;
  keywords: string[];
  minimum_evidence: number;
};

export type CriteriaSheet = {
  id: string;
  title: string;
  job_title: string;
  job_description: string;
  required_skills: string[];
  preferred_skills: string[];
  criteria: Criterion[];
  red_flags: string[];
};

export type ResumeSeed = {
  id: string;
  candidate_name: string;
  title: string;
  focus: string;
  source_file: string;
};

export type Evidence = {
  source: string;
  text: string;
  similarity: number;
};

export type CriterionScore = {
  label: string;
  weight: number;
  score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  evidence: Evidence[];
};

export type CandidateRanking = {
  candidate_id: string;
  candidate_name: string;
  resume_title: string;
  match_score: number;
  summary: string;
  pros: string[];
  cons: string[];
  criteria_breakdown: CriterionScore[];
  evidence: Evidence[];
};

export type RankingResponse = {
  criteria_id: string;
  criteria_title: string;
  job_title: string;
  total_candidates: number;
  ranking: CandidateRanking[];
  analysis_id: number | null;
};

