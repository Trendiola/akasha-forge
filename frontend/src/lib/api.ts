import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  headers: { "Content-Type": "application/json" },
});

export const API_BASE = `${BACKEND_URL}/api`;

export async function uploadFile(file: File, category = "general") {
  const form = new FormData();
  form.append("file", file);
  form.append("category", category);
  const res = await api.post("/files/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data as { id: string; url: string; original_filename: string };
}

export const fileUrl = (id: string) => `${API_BASE}/files/${id}`;
