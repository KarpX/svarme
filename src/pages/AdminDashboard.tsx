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
  Table,
  Tag,
  Badge,
  Tooltip,
  Statistic,
  Row,
  Col,
  Avatar,
} from "antd";
import { useEffect, useState } from "react";
import { quizStore, type Question } from "../stores/QuizStore";
import { gameStore } from "../stores/GameStore";
import Sider from "antd/es/layout/Sider";
import { Content } from "antd/es/layout/layout";
import {
  DashboardOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  StopOutlined,
  TeamOutlined,
  TrophyOutlined,
  UploadOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { authStore } from "../stores/AuthStore";

type ViewMode = "content" | "games";

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  waiting: { color: "default", label: "Лобби" },
  pending: { color: "processing", label: "Выбор режима" },
  choosing_question: { color: "blue", label: "Выбор вопроса" },
  answering: { color: "green", label: "Ответ" },
  cat_in_bag: { color: "purple", label: "Кот в мешке" },
  cat_in_bag_choosing: { color: "purple", label: "Кот: выбор игрока" },
  final_removing: { color: "orange", label: "Финал: удаление" },
  final_betting: { color: "gold", label: "Финал: ставки" },
  final_answering: { color: "volcano", label: "Финал: ответ" },
  finished: { color: "default", label: "Завершена" },
};

export const AdminDashboard = observer(() => {
  const [viewMode, setViewMode] = useState<ViewMode>("content");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [isQuestionModalOpen, setIsQuestionModalOpen] = useState(false);
  const [questionForm] = Form.useForm();
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);
  const [editingCategory, setEditingCategory] = useState<any | null>(null);
  const [selectedGame, setSelectedGame] = useState<any | null>(null);

  const openEditCategoryModal = (cat: any) => {
    setEditingCategory(cat);
    form.setFieldsValue({ title: cat.name, round: cat.round });
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
    if (success) message.success(`${file.name} успешно загружен`);
    else message.error(`Ошибка при загрузке ${file.name}`);
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
      success = await quizStore.updateQuestion(editingQuestion.id, {
        ...values,
        category_id: quizStore.selectedCategoryId!,
      });
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

  // Авто-рефреш игр каждые 10 секунд когда открыта вкладка
  useEffect(() => {
    if (viewMode !== "games") return;
    gameStore.fetchActiveGames();
    const interval = setInterval(() => gameStore.fetchActiveGames(), 10_000);
    return () => clearInterval(interval);
  }, [viewMode]);

  const groupedCategories = quizStore.categories.reduce(
    (acc, cat) => {
      if (!acc[cat.round]) acc[cat.round] = [];
      acc[cat.round].push(cat);
      return acc;
    },
    {} as Record<number, typeof quizStore.categories>,
  );

  // ── Games view ─────────────────────────────────────────────────

  const playerColumns = [
    {
      title: "Игрок",
      dataIndex: "username",
      key: "username",
      render: (username: string, record: any) => (
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Avatar size="small" icon={<UserOutlined />} />
          <span style={{ fontWeight: 500 }}>
            {username
              ? `@${username}`
              : record.first_name || `ID:${record.user_id}`}
          </span>
        </div>
      ),
    },
    {
      title: "Очки",
      dataIndex: "points",
      key: "points",
      render: (points: number) => (
        <span
          style={{
            color: points >= 0 ? "#52c41a" : "#ff4d4f",
            fontWeight: 600,
          }}
        >
          {points >= 0 ? "+" : ""}
          {points}
        </span>
      ),
      sorter: (a: any, b: any) => b.points - a.points,
    },
    {
      title: "User ID",
      dataIndex: "user_id",
      key: "user_id",
      render: (id: number) => (
        <code style={{ fontSize: 11, color: "#8c8c8c" }}>{id}</code>
      ),
    },
  ];

  const gameColumns = [
    {
      title: "Chat ID",
      dataIndex: "chat_id",
      key: "chat_id",
      render: (id: number) => (
        <code style={{ color: "#1890ff", fontSize: 12 }}>{id}</code>
      ),
    },
    {
      title: "Режим",
      dataIndex: "game_mode",
      key: "game_mode",
      render: (mode: string) => (
        <Tag>{mode === "blitz" ? "⚡ Блиц" : "🕹 Обычный"}</Tag>
      ),
    },
    {
      title: "Статус",
      dataIndex: "status",
      key: "status",
      render: (status: string) => {
        const cfg = STATUS_CONFIG[status] || { color: "blue", label: status };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "Раунд",
      dataIndex: "current_round",
      key: "current_round",
      render: (round: number) => (
        <Badge count={round} showZero color="#faad14" />
      ),
    },
    {
      title: "Игроки",
      dataIndex: "players",
      key: "players_count",
      render: (players: any[]) => (
        <span>
          <TeamOutlined style={{ marginRight: 4 }} />
          {players?.length ?? 0}
        </span>
      ),
    },
    {
      title: "Лидер",
      dataIndex: "players",
      key: "leader",
      render: (players: any[]) => {
        if (!players?.length) return "—";
        const leader = [...players].sort((a, b) => b.points - a.points)[0];
        const name = leader.username
          ? `@${leader.username}`
          : leader.first_name || `ID:${leader.user_id}`;
        return (
          <span>
            <TrophyOutlined style={{ color: "#faad14", marginRight: 4 }} />
            {name} ({leader.points})
          </span>
        );
      },
    },
    {
      title: "",
      key: "actions",
      render: (_: any, record: any) => (
        <div style={{ display: "flex", gap: 8 }}>
          <Tooltip title="Подробнее">
            <Button
              size="small"
              icon={<DashboardOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                setSelectedGame(record);
              }}
            />
          </Tooltip>
          <Popconfirm
            title="Принудительно завершить игру?"
            onConfirm={(e) => {
              e?.stopPropagation();
              gameStore.forceStop(record.id);
            }}
            okText="Да"
            cancelText="Нет"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Остановить">
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={(e) => e.stopPropagation()}
              />
            </Tooltip>
          </Popconfirm>
        </div>
      ),
    },
  ];

  const renderGamesView = () => {
    const games = gameStore.activeGames ?? [];
    const activeCount = games.filter(
      (g) => !["waiting", "pending", "finished"].includes(g.status),
    ).length;
    const lobbyCount = games.filter((g) =>
      ["waiting", "pending"].includes(g.status),
    ).length;
    const totalPlayers = games.reduce(
      (sum, g) => sum + (g.players?.length ?? 0),
      0,
    );

    return (
      <div>
        {/* Статистика сверху */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="Всего игр"
                value={games.length}
                prefix={<DashboardOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="Активных"
                value={activeCount}
                valueStyle={{ color: "#52c41a" }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="В лобби"
                value={lobbyCount}
                valueStyle={{ color: "#1890ff" }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="Игроков онлайн"
                value={totalPlayers}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <h2 style={{ margin: 0 }}>Игровые сессии</h2>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => gameStore.fetchActiveGames()}
            loading={gameStore.isLoading}
          >
            Обновить
          </Button>
        </div>

        {gameStore.isLoading && !games.length ? (
          <div style={{ textAlign: "center", marginTop: 80 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Table
            dataSource={games}
            columns={gameColumns}
            rowKey="id"
            pagination={{ pageSize: 20 }}
            size="small"
            onRow={(record) => ({
              onClick: () => setSelectedGame(record),
              style: { cursor: "pointer" },
            })}
            locale={{ emptyText: <Empty description="Нет активных игр" /> }}
          />
        )}

        {/* Модалка с деталями игры */}
        <Modal
          title={`Игра #${selectedGame?.id} — чат ${selectedGame?.chat_id}`}
          open={!!selectedGame}
          onCancel={() => setSelectedGame(null)}
          footer={[
            <Popconfirm
              key="stop"
              title="Принудительно завершить игру?"
              onConfirm={() => {
                gameStore.forceStop(selectedGame.id);
                setSelectedGame(null);
              }}
              okText="Да"
              cancelText="Нет"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<StopOutlined />}>
                Остановить игру
              </Button>
            </Popconfirm>,
            <Button key="close" onClick={() => setSelectedGame(null)}>
              Закрыть
            </Button>,
          ]}
          width={640}
        >
          {selectedGame && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Основная инфо */}
              <Row gutter={12}>
                <Col span={8}>
                  <Card size="small" title="Статус">
                    {(() => {
                      const cfg = STATUS_CONFIG[selectedGame.status] || {
                        color: "blue",
                        label: selectedGame.status,
                      };
                      return (
                        <Tag color={cfg.color} style={{ fontSize: 13 }}>
                          {cfg.label}
                        </Tag>
                      );
                    })()}
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" title="Раунд">
                    <span style={{ fontSize: 20, fontWeight: 600 }}>
                      {selectedGame.current_round}
                    </span>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" title="Режим">
                    <Tag>
                      {selectedGame.game_mode === "blitz"
                        ? "⚡ Блиц"
                        : "🕹 Обычный"}
                    </Tag>
                  </Card>
                </Col>
              </Row>

              {/* Текущий вопрос */}
              {selectedGame.active_question_id && (
                <Card
                  size="small"
                  title="Активный вопрос"
                  style={{ background: "#fffbe6", borderColor: "#ffe58f" }}
                >
                  <code>ID: {selectedGame.active_question_id}</code>
                  {selectedGame.choosing_user_id && (
                    <div
                      style={{ marginTop: 4, color: "#8c8c8c", fontSize: 12 }}
                    >
                      Отвечает: <code>{selectedGame.choosing_user_id}</code>
                    </div>
                  )}
                  {selectedGame.remaining_seconds != null && (
                    <div
                      style={{ marginTop: 4, color: "#ff4d4f", fontSize: 12 }}
                    >
                      Осталось: {selectedGame.remaining_seconds} сек
                    </div>
                  )}
                </Card>
              )}

              {/* Таблица игроков */}
              <div>
                <div style={{ fontWeight: 500, marginBottom: 8 }}>
                  <TeamOutlined /> Игроки ({selectedGame.players?.length ?? 0})
                </div>
                <Table
                  dataSource={selectedGame.players ?? []}
                  columns={playerColumns}
                  rowKey="user_id"
                  pagination={false}
                  size="small"
                  locale={{ emptyText: "Нет игроков" }}
                />
              </div>
            </div>
          )}
        </Modal>
      </div>
    );
  };

  // ── Categories view ────────────────────────────────────────────

  const renderContentView = () => {
    if (quizStore.isLoading) {
      return (
        <div style={{ textAlign: "center", marginTop: 50 }}>
          <Spin size="large" />
        </div>
      );
    }
    if (!quizStore.selectedCategoryId) {
      return (
        <Empty
          description="Выберите категорию слева, чтобы увидеть вопросы"
          style={{ marginTop: 100 }}
        />
      );
    }
    return (
      <>
        <h2>
          Вопросы:{" "}
          {
            quizStore.categories.find(
              (c) => c.id === quizStore.selectedCategoryId,
            )?.name
          }
        </h2>
        <div style={{ display: "flex", gap: 15, marginBottom: 20 }}>
          <Button
            type="primary"
            icon={<PlusCircleOutlined />}
            onClick={() => setIsQuestionModalOpen(true)}
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
                  <div style={{ display: "flex", gap: 10 }}>
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
                      <Button type="text" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </div>
                }
              >
                <p>{q.text}</p>
                <div style={{ color: "#52c41a" }}>
                  <strong>Ответ:</strong> {q.answer.join(", ")}
                </div>
              </Card>
            </List.Item>
          )}
        />
      </>
    );
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={240}
        theme="light"
        style={{ borderRight: "1px solid #f0f0f0" }}
      >
        <Menu
          mode="inline"
          selectedKeys={[
            viewMode === "games"
              ? "menu-games"
              : String(quizStore.selectedCategoryId),
          ]}
          defaultOpenKeys={["sub-content"]}
          style={{ height: "100%" }}
        >
          <Menu.Item
            key="menu-games"
            icon={<DashboardOutlined />}
            onClick={() => setViewMode("games")}
          >
            Активные игры
            {(gameStore.activeGames?.length ?? 0) > 0 && (
              <Badge
                count={gameStore.activeGames?.length}
                size="small"
                style={{ marginLeft: 8 }}
              />
            )}
          </Menu.Item>

          <Menu.SubMenu
            key="sub-content"
            icon={<DatabaseOutlined />}
            title="Управление вопросами"
            onTitleClick={() => setViewMode("content")}
          >
            <div
              style={{
                padding: "6px 16px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <small style={{ color: "#8c8c8c" }}>КАТЕГОРИИ</small>
              <Button
                type="text"
                icon={<PlusOutlined />}
                size="small"
                onClick={() => {
                  setEditingCategory(null);
                  form.resetFields();
                  setIsModalOpen(true);
                }}
              />
            </div>

            {Object.keys(groupedCategories)
              .sort((a, b) => Number(a) - Number(b))
              .map((round) => (
                <Menu.ItemGroup key={`round-${round}`} title={`Раунд ${round}`}>
                  {groupedCategories[Number(round)].map((cat) => (
                    <Menu.Item
                      key={String(cat.id)}
                      onClick={() => {
                        setViewMode("content");
                        quizStore.selectCategory(cat.id);
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          width: "100%",
                        }}
                      >
                        <span
                          style={{
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            flex: 1,
                          }}
                        >
                          {cat.name}
                        </span>
                        <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
                          <EditOutlined
                            style={{ fontSize: 12, color: "#1890ff" }}
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
                              style={{ fontSize: 12, color: "#ff4d4f" }}
                              onClick={(e) => e.stopPropagation()}
                            />
                          </Popconfirm>
                        </div>
                      </div>
                    </Menu.Item>
                  ))}
                </Menu.ItemGroup>
              ))}
          </Menu.SubMenu>
        </Menu>
      </Sider>

      {/* ── Основной контент ── */}
      <Layout>
        <Content style={{ padding: "24px", background: "#fff" }}>
          {viewMode === "games" ? renderGamesView() : renderContentView()}
        </Content>
      </Layout>

      {/* ── Модалки ── */}
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

      <Modal
        title={editingQuestion ? "Редактировать вопрос" : "Новый вопрос"}
        open={isQuestionModalOpen}
        onOk={handleSaveQuestion}
        onCancel={() => setIsQuestionModalOpen(false)}
        okText={editingQuestion ? "Сохранить" : "Создать"}
        cancelText="Отмена"
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
