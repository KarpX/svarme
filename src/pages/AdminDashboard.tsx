import { observer } from "mobx-react-lite";
import {
  List,
  Card,
  Layout,
  Menu,
  Empty,
  Spin,
  Form,
  message,
  Button,
  Modal,
  Input,
  InputNumber,
  Upload,
  Popconfirm,
} from "antd";
import { useEffect, useState } from "react";
import { quizStore, type Question } from "../stores/QuizStore";
import Sider from "antd/es/layout/Sider";
import { Content } from "antd/es/layout/layout";
import {
  DeleteOutlined,
  EditOutlined,
  PlusCircleOutlined,
  PlusOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { authStore } from "../stores/AuthStore";

export const AdminDashboard = observer(() => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();

  const [isQuestionModalOpen, setIsQuestionModalOpen] = useState(false);
  const [questionForm] = Form.useForm();

  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);
  const [editingCategory, setEditingCategory] = useState<any | null>(null);

  // const handleCreate = async () => {
  //   const values = await form.validateFields();
  //   const success = await quizStore.addCategory(values.title, values.round);
  //   if (success) {
  //     message.success("Категория создана!");
  //     setIsModalOpen(false);
  //     form.resetFields();
  //   } else {
  //     message.error("Не удалось создать категорию");
  //   }
  // };

  // const handleCreateQuestion = async () => {
  //   const values = await questionForm.validateFields();
  //   const success = await quizStore.addQuestion(
  //     values.title,
  //     values.answer,
  //     values.price,
  //     quizStore.selectedCategoryId!,
  //   );

  //   if (success) {
  //     message.success("Вопрос добавлен!");
  //     setIsQuestionModalOpen(false);
  //     questionForm.resetFields();
  //   }
  // };

  const openEditCategoryModal = (cat: any) => {
    setEditingCategory(cat);
    form.setFieldsValue({ title: cat.name, round: cat.round }); // ВАЖНО: имя поля в форме 'title'
    setIsModalOpen(true);
  };

  const handleSaveCategory = async () => {
    const values = await form.validateFields();
    let success;

    if (editingCategory) {
      success = await quizStore.updateCategory(
        editingCategory.id,
        values.title,
        values.round,
      );
    } else {
      success = await quizStore.addCategory(values.title, values.round);
    }

    if (success) {
      message.success(
        editingCategory ? "Категория обновлена" : "Категория создана",
      );
      setIsModalOpen(false);
      setEditingCategory(null);
      form.resetFields();
    }
  };

  const handleUpload = async (info: any) => {
    const { file } = info;
    const success = await quizStore.importBulkQuestions(
      file as File,
      quizStore.selectedCategoryId!,
    );

    if (success) {
      message.success(`${file.name} успешно загружен`);
    } else {
      message.error(`Ошибка при загрузке ${file.name}`);
    }
  };

  const openEditModal = (q: Question) => {
    setEditingQuestion(q);
    questionForm.setFieldsValue(q);
    setIsQuestionModalOpen(true);
  };

  const handleSaveQuestion = async () => {
    const values = await questionForm.validateFields();
    let success;

    if (editingQuestion) {
      const updateData = {
        ...values,
        category_id: quizStore.selectedCategoryId!,
      };
      success = await quizStore.updateQuestion(editingQuestion.id, updateData);
    } else {
      success = await quizStore.addQuestion(
        values.text,
        values.answer,
        values.price,
        quizStore.selectedCategoryId!,
      );
    }

    if (success) {
      message.success(editingQuestion ? "Вопрос обновлен" : "Вопрос добавлен");
      setIsQuestionModalOpen(false);
      setEditingQuestion(null);
      questionForm.resetFields();
    }
  };

  useEffect(() => {
    quizStore.fetchCategories();
    authStore.checkAuth();
  }, []);

  const groupedCategories = quizStore.categories.reduce(
    (acc, cat) => {
      if (!acc[cat.round]) acc[cat.round] = [];
      acc[cat.round].push(cat);
      return acc;
    },
    {} as Record<number, typeof quizStore.categories>,
  );

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={250}
        theme="light"
        style={{ borderRight: "1px solid #f0f0f0" }}
      >
        <div
          style={{
            padding: "16px",
            fontWeight: "bold",
            fontSize: "18px",
            color: "black",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>📂 Категории</span>
          <Button
            type="primary"
            shape="circle"
            icon={<PlusOutlined />}
            size="small"
            onClick={() => {
              setEditingCategory(null);
              form.resetFields();
              setIsModalOpen(true);
            }}
            style={{ marginRight: 5 }}
          />
        </div>
        <Menu
          mode="inline"
          selectedKeys={[String(quizStore.selectedCategoryId)]}
          onClick={({ key }) => {
            if (!key.startsWith("round-")) {
              quizStore.selectCategory(Number(key));
            }
          }}
          items={Object.keys(groupedCategories)
            .sort((a, b) => Number(a) - Number(b))
            .map((round) => ({
              key: `round-${round}`,
              label: `Раунд ${round}`,
              type: "group",
              children: groupedCategories[Number(round)].map((cat) => ({
                key: String(cat.id),
                label: (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>{cat.name}</span>
                    <div>
                      <EditOutlined
                        style={{ fontSize: "12px", color: "#1890ff" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          openEditCategoryModal(cat);
                        }}
                      />
                      <Popconfirm
                        title="Удалить категорию и все её вопросы?"
                        onConfirm={(e) => {
                          e?.stopPropagation();
                          quizStore.deleteCategory(cat.id);
                        }}
                        onCancel={(e) => e?.stopPropagation()}
                        okText="Да"
                        cancelText="Нет"
                      >
                        <DeleteOutlined
                          style={{ fontSize: "12px", color: "#ff4d4f" }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Popconfirm>
                    </div>
                  </div>
                ),
              })),
            }))}
        />
      </Sider>

      <Modal
        title={editingCategory ? "Редактировать категорию" : "Новая категория"}
        open={isModalOpen}
        onOk={handleSaveCategory}
        onCancel={() => setIsModalOpen(false)}
        okText={editingCategory ? "Сохранить" : "Создать"}
        cancelText="Отмена"
      >
        <Form form={form} layout="vertical" initialValues={{ round: 1 }}>
          <Form.Item
            name="title"
            label="Название категории"
            rules={[{ required: true, message: "Введите название" }]}
          >
            <Input placeholder="Например: Кино" />
          </Form.Item>
          <Form.Item
            name="round"
            label="Номер раунда"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={10} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>

      <Layout>
        <Content style={{ padding: "24px", background: "#fff" }}>
          {quizStore.isLoading ? (
            <div style={{ textAlign: "center", marginTop: 50 }}>
              <Spin size="large" />
            </div>
          ) : quizStore.selectedCategoryId ? (
            <>
              <h2>
                Вопросы категории:{" "}
                {
                  quizStore.categories.find(
                    (c) => c.id === quizStore.selectedCategoryId,
                  )?.name
                }
              </h2>
              <div style={{ display: "flex", gap: 15 }}>
                <Button
                  type="primary"
                  icon={<PlusCircleOutlined />}
                  onClick={() => setIsQuestionModalOpen(true)}
                  style={{ marginBottom: 20 }}
                >
                  Добавить вопрос
                </Button>
                <Upload
                  beforeUpload={() => false}
                  onChange={handleUpload}
                  showUploadList={false}
                  accept=".json"
                >
                  <Button icon={<UploadOutlined />}>Импорт JSON</Button>
                </Upload>
              </div>
              <List
                grid={{ gutter: 16, column: 1 }}
                dataSource={quizStore.questions}
                renderItem={(q) => (
                  <List.Item>
                    <Card
                      size="small"
                      title={`Цена: ${q.price}`}
                      extra={
                        <div style={{ display: "flex", gap: "10px" }}>
                          <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => openEditModal(q)}
                          />
                          <Popconfirm
                            title="Удалить этот вопрос?"
                            onConfirm={() => quizStore.deleteQuestion(q.id)}
                            okText="Да"
                            cancelText="Нет"
                          >
                            <Button
                              type="text"
                              danger
                              icon={<DeleteOutlined />}
                            />
                          </Popconfirm>
                        </div>
                      }
                    >
                      <p>{q.text}</p>
                      <div style={{ color: "#52c41a" }}>
                        <strong>Ответ:</strong> {q.answer}
                      </div>
                    </Card>
                  </List.Item>
                )}
              />
            </>
          ) : (
            <Empty
              description="Выберите категорию слева, чтобы увидеть вопросы"
              style={{ marginTop: 100 }}
            />
          )}
        </Content>
      </Layout>
      <Modal
        title={editingQuestion ? "Редактировать вопрос" : "Новый вопрос"}
        open={isQuestionModalOpen}
        onOk={handleSaveQuestion}
        onCancel={() => setIsQuestionModalOpen(false)}
        okText={editingQuestion ? "Сохранить" : "Создать"}
      >
        <Form
          form={questionForm}
          layout="vertical"
          initialValues={{ price: 100 }}
        >
          <Form.Item
            name="text"
            label="Текст вопроса"
            rules={[{ required: true }]}
          >
            <Input.TextArea rows={3} placeholder="В каком году...?" />
          </Form.Item>
          <Form.Item
            name="answer"
            label="Правильный ответ"
            rules={[{ required: true }]}
          >
            <Input placeholder="1961" />
          </Form.Item>
          <Form.Item
            name="price"
            label="Сложность (очки)"
            rules={[{ required: true }]}
          >
            <InputNumber min={100} step={100} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
});
