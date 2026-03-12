import { makeAutoObservable, runInAction } from "mobx";
import axios from "axios";

export interface Question {
  id: number;
  text: string;
  answer: string;
  price: number;
}

export interface Category {
  id: number;
  name: string;
  round: number;
}

class QuizStore {
  categories: Category[] = [];
  questions: Question[] = [];
  selectedCategoryId: number | null = null;
  isLoading: boolean = false;

  constructor() {
    makeAutoObservable(this);
  }

  fetchCategories = async () => {
    this.isLoading = true;
    try {
      const res = await axios.get<Category[]>("admin/categories", {
        withCredentials: true,
      });
      runInAction(() => {
        this.categories = res.data;
        this.isLoading = false;
      });
    } catch (e) {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };

  selectCategory = async (id: number) => {
    this.selectedCategoryId = id;
    this.isLoading = true;
    try {
      const res = await axios.get<Question[]>(
        `/admin/questions?category_id=${id}`,
        { withCredentials: true },
      );
      runInAction(() => {
        this.questions = res.data.sort((a, b) => a.price - b.price);
        this.isLoading = false;
      });
    } catch (e) {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };

  addCategory = async (name: string, round: number) => {
    try {
      const res = await axios.post(
        "admin/categories",
        { name, round },
        { withCredentials: true },
      );

      if (res.data && res.data.id) {
        runInAction(() => {
          this.categories.push(res.data);
          this.categories = this.categories.sort((a, b) => a.round - b.round);
        });
        return true;
      }
      return false;
    } catch (e) {
      console.error("Ошибка при создании категории", e);
      return false;
    }
  };

  updateCategory = async (id: number, name: string, round: number) => {
    try {
      const res = await axios.patch(
        `/admin/categories?category_id=${id}`,
        { id, name, round },
        { withCredentials: true },
      );
      if (res.data && res.data.id) {
        runInAction(() => {
          const index = this.categories.findIndex((c) => c.id === id);
          if (index !== -1) this.categories[index] = res.data;
        });
        return true;
      }
      return false;
    } catch (e) {
      console.error(e);
      return false;
    }
  };

  deleteCategory = async (id: number) => {
    try {
      const res = await axios.delete(`/admin/categories?category_id=${id}`, {
        withCredentials: true,
      });
      if (res.status === 200 || res.data.ok) {
        runInAction(() => {
          this.categories = this.categories.filter((c) => c.id !== id);
          if (this.selectedCategoryId === id) {
            this.selectedCategoryId = null;
            this.questions = [];
          }
        });
        return true;
      }
      return false;
    } catch (e) {
      console.error("Ошибка при удалении категории", e);
      return false;
    }
  };

  addQuestion = async (
    text: string,
    answer: string,
    price: number,
    categoryId: number,
  ) => {
    try {
      const res = await axios.post(
        "/admin/questions",
        { text, answer, price, category_id: categoryId },
        { withCredentials: true },
      );

      if (res.data && res.data.id) {
        runInAction(() => {
          this.questions.push(res.data);
          this.questions = this.questions.sort((a, b) => a.price - b.price);
        });
        return true;
      }
      return false;
    } catch (e) {
      console.error("Failed to add question", e);
      return false;
    }
  };

  updateQuestion = async (id: number, data: Partial<Question>) => {
    try {
      const res = await axios.patch(
        `/admin/questions?question_id=${id}`,
        { id, ...data },
        { withCredentials: true },
      );
      if (res.data && res.data.id) {
        runInAction(() => {
          const index = this.questions.findIndex((q) => q.id === id);
          if (index !== -1) {
            this.questions[index] = res.data;
            this.questions = this.questions.sort((a, b) => a.price - b.price);
          }
        });
        return true;
      }
      return false;
    } catch (e) {
      console.error(e);
      return false;
    }
  };

  deleteQuestion = async (id: number) => {
    try {
      const res = await axios.delete(`/admin/questions?question_id=${id}`, {
        withCredentials: true,
      });
      if (res.status === 200 || res.data.ok) {
        runInAction(() => {
          this.questions = this.questions.filter((q) => q.id !== id);
        });
        return true;
      }
      return false;
    } catch (e) {
      console.error("Ошибка при удалении вопроса", e);
      return false;
    }
  };

  importBulkQuestions = async (file: File, categoryId: number) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post(
        `admin/questions/import?category_id=${categoryId}`,
        formData,
        {
          withCredentials: true,
          headers: { "Content-Type": "multipart/form-data" },
        },
      );

      if (res.data.ok) {
        runInAction(() => {
          this.questions = [...this.questions, ...res.data.questions].sort(
            (a, b) => a.price - b.price,
          );
        });
        return true;
      }
    } catch (e) {
      console.error("Import failed", e);
      return false;
    }
  };
}

export const quizStore = new QuizStore();
