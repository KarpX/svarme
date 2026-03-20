import { makeAutoObservable, runInAction } from "mobx";

export interface Player {
  user_id: number;
  username: string | null;
  first_name: string | null;
  points: number;
}

export interface Game {
  id: number;
  chat_id: number;
  status: string;
  game_mode: string;
  current_round: number;
  active_question_id: number | null;
  choosing_user_id: number | null;
  target_user_id: number | null;
  remaining_seconds: number | null;
  players: Player[];
}

class GameStore {
  activeGames: Game[] = [];
  isLoading = false;
  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  async fetchActiveGames(): Promise<void> {
    this.isLoading = true;
    this.error = null;
    try {
      const res = await fetch("/admin/games", { credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Game[] = await res.json();
      runInAction(() => {
        this.activeGames = data;
      });
    } catch (e: any) {
      runInAction(() => {
        this.error = e.message ?? "Ошибка загрузки игр";
      });
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  }

  async forceStop(gameId: number): Promise<void> {
    try {
      const res = await fetch(`/admin/games/${gameId}/stop`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Убираем игру из списка сразу, не ждём рефреша
      runInAction(() => {
        this.activeGames = this.activeGames.filter((g) => g.id !== gameId);
      });
    } catch (e: any) {
      runInAction(() => {
        this.error = e.message ?? "Ошибка остановки игры";
      });
    }
  }
}

export const gameStore = new GameStore();
