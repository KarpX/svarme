import { observer, useLocalObservable } from "mobx-react-lite";
import { Button, List, Card } from "antd"; // Добавил List и Card для красоты
import { useState, useEffect } from "react";
import axios, { type AxiosResponse } from "axios";
import { makeAutoObservable } from "mobx";

import viteLogo from "/kts.svg";
import s from "/src/App.module.css";

interface Question {
  id: number;
  text: string;
  answer: string;
  price: number;
}

class Counter {
  count: number = 0;

  constructor(initial: number = 0) {
    this.count = initial;
    makeAutoObservable(this);
    this.increment = this.increment.bind(this);
  }

  increment() {
    this.count++;
  }
}

export const AdminDashboard = observer(() => {
  const counter = useLocalObservable(() => new Counter());
  const [questions, setQuestions] = useState<Question[]>([]);

  useEffect(() => {
    axios
      .get<Question[]>("/admin/questions")
      .then((response: AxiosResponse<Question[]>) => {
        setQuestions(response.data);
      })
      .catch((err) => console.error("Ошибка API:", err));
  }, []);

  return (
    <div className={s.app}>
      <img src={viteLogo} className={s.logo} alt="logo" />

      <div style={{ marginBottom: 20 }}>
        <Button type="primary" onClick={counter.increment}>
          Количество кликов: {counter.count}
        </Button>
      </div>

      <div className={s.content}>
        <h2>Список вопросов</h2>
        <List
          grid={{ gutter: 16, column: 1 }}
          dataSource={questions}
          renderItem={(item) => (
            <List.Item>
              <Card title={`Вопрос №${item.id} (${item.price} очков)`}>
                {item.text}
                <div style={{ marginTop: 10, color: "gray" }}>
                  Ответ: {item.answer}
                </div>
              </Card>
            </List.Item>
          )}
        />
      </div>
    </div>
  );
});
