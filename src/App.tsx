import { observer } from "mobx-react-lite";
import { useEffect } from "react";
import { authStore } from "./stores/AuthStore";
import { LoginPage } from "./pages/LoginPage";
import { AdminDashboard } from "./pages/AdminDashboard"; // Вынеси туда свой текущий код со списком
import { Spin } from "antd";

const App = observer(() => {
  // Проверяем авторизацию один раз при запуске
  useEffect(() => {
    authStore.checkAuth();
  }, []);

  // Пока проверяем куки — показываем крутилку
  if (!authStore.initialized) {
    return (
      <div
        style={{ display: "flex", justifyContent: "center", marginTop: 100 }}
      >
        <Spin size="large" tip="Загрузка..." />
      </div>
    );
  }

  // Главный выбор: логин или админка
  return authStore.isAuth ? <AdminDashboard /> : <LoginPage />;
});

export default App;
