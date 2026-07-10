import axios from "axios";
import type { CriteriaSheet, RankingResponse, ResumeSeed } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export async function getDefaultCriteria(): Promise<CriteriaSheet> {
  const response = await axios.get<CriteriaSheet>(`${API_URL}/api/criteria/default`);
  return response.data;
}

export async function getSeedResumes(): Promise<ResumeSeed[]> {
  const response = await axios.get<ResumeSeed[]>(`${API_URL}/api/resumes/seed`);
  return response.data;
}

export async function analyzeSeed(
  criteriaSheet: CriteriaSheet,
  topK = 5,
): Promise<RankingResponse> {
  const response = await axios.post<RankingResponse>(`${API_URL}/api/analyze/seed`, {
    criteria_sheet: criteriaSheet,
    top_k: topK,
  });
  return response.data;
}

export async function analyzeDocuments(
  criteriaFile: File,
  files: File[],
  topK = 5,
): Promise<RankingResponse> {
  const formData = new FormData();
  formData.append("criteria_file", criteriaFile);
  files.forEach((file) => formData.append("files", file));
  formData.append("top_k", String(topK));

  const response = await axios.post<RankingResponse>(
    `${API_URL}/api/analyze/documents`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return response.data;
}
