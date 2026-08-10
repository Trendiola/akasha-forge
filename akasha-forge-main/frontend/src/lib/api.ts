import axios from "axios";
import { toast } from "sonner";
import { resolveBackendUrl } from "./runtime";

export const BACKEND_URL = resolveBackendUrl();

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  headers: { "Content-Type": "application/json" },
});

// Safety net: surface gateway/network failures (e.g. 502/503/504 during a
// backend restart) as a friendly toast instead of a silent failure or overlay.
let lastGatewayToast = 0;
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status;
    const isGateway = !error?.response || [502, 503, 504].includes(status);
    if (isGateway) {
      const now = Date.now();
      if (now - lastGatewayToast > 3000) {
        lastGatewayToast = now;
        toast.error("The server is briefly unavailable. Please try again in a moment.");
      }
    }
    return Promise.reject(error);
  }
);

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
