import { Form, Input, Button, Card, message } from "antd";
import { authStore } from "../stores/AuthStore";
import { observer } from "mobx-react-lite";

export const LoginPage = observer(() => {
  const onFinish = async (values: any) => {
    const success = await authStore.login(values.email, values.password);
    if (success) {
      message.success("Добро пожаловать!");
    } else {
      message.error("Неверный логин или пароль");
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
        background: "#f0f2f5",
      }}
    >
      <Card title="Вход в Svarme Admin" style={{ width: 400 }}>
        <Form onFinish={onFinish} layout="vertical">
          <Form.Item name="email" label="Email" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="password"
            label="Пароль"
            rules={[{ required: true }]}
          >
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Войти
          </Button>
        </Form>
      </Card>
    </div>
  );
});
