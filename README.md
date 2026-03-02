## Что внутри

- **React 19** 
- **TypeScript** 
- **Vite**
- **Mobx** — состояние приложения
- **Tanstack query** — серверное состояние
- **Ant Design (antd)** — кнопки, формы, таблицы, модалки из коробки
- **CSS Modules** — стили к компонентам без глобальных конфликтов

## Быстрый старт

```bash
# Установка зависимостей (npm или yarn)
npm install
# или
yarn

# Запуск dev-сервера (обычно http://localhost:5173)
npm run dev
# или
yarn dev
```

Открой в браузере адрес из терминала — увидишь стартовую страницу с кнопкой-счётчиком.

## Скрипты

| Команда | Описание |
|--------|----------|
| `npm run dev` | Запуск в режиме разработки с hot-reload |
| `npm run build` | Сборка в папку `dist` (для деплоя) |
| `npm run preview` | Локальный просмотр собранного билда |
| `npm run lint` | Проверка кода линтером |

## UI из коробки (Ant Design)

Уже подключён **antd** — можно сразу использовать кнопки, инпуты, таблицы, модалки:

```tsx
import { Button, Input, Table, Modal } from 'antd'

// Кнопка
<Button type="primary">Сохранить</Button>

// Поле ввода
<Input placeholder="Имя" />

// Таблица (колонки + dataSource как у тебя с бэка)
<Table columns={columns} dataSource={items} rowKey="id" />
```

Документация: [ant.design](https://ant.design/components/overview/)

## Стили (CSS Modules)

Файлы вида `*.module.css` дают локальные классы — не конфликтуют с другими компонентами.

В компоненте:

```tsx
import s from './App.module.css'

<div className={s.myBlock}>...</div>
```

В `App.module.css`:

```css
.myBlock {
  padding: 1rem;
  border-radius: 8px;
}
```

## Что делать дальше

1. Замени содержимое `App.tsx` на свой первый экран.
2. Новые экраны/компоненты — создавай файлы в `src/` (например `src/components/`, `src/pages/`)
3. Для нескольких страниц добавь [роутер](https://reactrouter.com/): `npm i react-router` и настрой маршруты в `App.tsx`.
4. Для состояния нужно взять [mobx](https://mobx.js.org/README.html) + Context API.
5. Для запросов рекомендуется использовать [Tanstack Query](https://tanstack.com/query/latest)
