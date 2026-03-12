import { makeAutoObservable, runInAction } from "mobx";
import axios from "axios";

class AuthStore {
  isAuth = false;
  userEmail = "";
  initialized = false;

  constructor() {
    makeAutoObservable(this);
  }

  login = async (email: string, pass: string) => {
    try {
      const res = await axios.post(
        "/admin/login",
        { email, password: pass },
        { withCredentials: true },
      );

      if (res.data.ok) {
        runInAction(() => {
          this.isAuth = true;
          this.userEmail = email;
          this.initialized = true;
        });
        return true;
      }
    } catch (e) {
      console.error("Login failed");
      return false;
    }
  };

  checkAuth = async () => {
    try {
      const res = await axios.get("/admin/categories", {
        withCredentials: true,
      });

      runInAction(() => {
        this.isAuth = true;
        this.userEmail = res.data.email;
        this.initialized = true;
      });
    } catch (e: any) {
      runInAction(() => {
        this.isAuth = false;
        this.initialized = true;
      });
      console.log("Пользователь не авторизован");
    }
  };
}

export const authStore = new AuthStore();
