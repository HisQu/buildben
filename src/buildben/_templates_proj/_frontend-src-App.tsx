import { useState } from 'react';

type AppProps = {
  projectName: string;
};

export function App({ projectName }: AppProps) {
  const [count, setCount] = useState(0);

  return (
    <main>
      <h1>{projectName}</h1>
      <p role="status">Count: {count}</p>
      <button onClick={() => setCount((currentCount) => currentCount + 1)}>
        Increment
      </button>
    </main>
  );
}
