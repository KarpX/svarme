import { makeAutoObservable } from 'mobx';
import { observer, useLocalObservable } from 'mobx-react-lite';
import { Button } from 'antd';

import viteLogo from '/kts.svg'

import s from './App.module.css'

class Counter {
  count: number = 0

  constructor(initial: number = 0) {
    this.count = initial

    makeAutoObservable(this)

    this.increment = this.increment.bind(this)
  }

  increment() {
    this.count++
  }
}

function App() {
  const counter = useLocalObservable(() => new Counter())

  return (
    <div className={s.app}>
      <img src={viteLogo} className={s.logo} alt="logo" />


      <Button onClick={counter.increment}>
        count is {counter.count}
      </Button>
    </div>
  )
}

export default observer(App)
