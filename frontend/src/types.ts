export interface Transcript { id: string; filename: string; expert: string; role: string; market: string; created_at: string }
export interface Passage { ordinal: number; timestamp: string; seconds: number; speaker: string; is_expert: boolean; text: string; start_offset: number; end_offset: number }
export interface Detail extends Transcript { passages: Passage[] }
export interface ImportResult { added: number; duplicates: number }
