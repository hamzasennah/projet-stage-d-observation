import axios from "axios";
import type { RankingResponse } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001";

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

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Erreur inattendue";
}
