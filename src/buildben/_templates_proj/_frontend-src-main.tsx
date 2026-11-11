import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Expected an element with id="root" in index.html.');
}

createRoot(rootElement).render(
  <StrictMode>
    <App projectName="<my_project>" />
  </StrictMode>,
);
