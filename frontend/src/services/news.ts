
import Cookies from "js-cookie";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

export interface NewsItem {
    id: number;
    title: string;
    summary: string;
    content?: string;
    published_at: string;
    status: string;
    tags?: string[];
    source_urls?: string[];
    updated_at?: string;
}

export const NewsService = {
    async getNews(page: number = 1, limit: number = 20, status?: string): Promise<NewsItem[]> {
        const token = Cookies.get("token");
        const offset = (page - 1) * limit;
        let url = `${API_URL}/news?limit=${limit}&offset=${offset}`;
        if (status) {
            url += `&status=${status}`;
        }

        const res = await fetch(url, {
            headers: { Authorization: `Bearer ${token}` }
        });

        if (!res.ok) {
            throw new Error("Failed to fetch news");
        }
        return res.json();
    },

    async getNewsItem(id: number): Promise<NewsItem> {
        const token = Cookies.get("token");
        const res = await fetch(`${API_URL}/news/${id}`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        if (!res.ok) {
            throw new Error("Failed to fetch news item");
        }
        return res.json();
    },

    async generateArticle(id: number): Promise<void> {
        const token = Cookies.get("token");
        const res = await fetch(`${API_URL}/news/${id}/generate`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` }
        });

        if (!res.ok) {
            throw new Error("Failed to generate article");
        }
    }
};
