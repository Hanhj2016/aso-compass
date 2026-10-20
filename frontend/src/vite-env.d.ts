/// <reference types="vite/client" />

interface Window {
  huggingface?: {
    variables?: {
      VITE_API_BASE_URL?: string;
    };
  };
}
