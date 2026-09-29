import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';

const App = React.lazy(() => import('./App'));
const ProjectOverview = import.meta.env.DEV && window.location.pathname === '/project'
  ? React.lazy(() => import('./pages/ProjectOverview'))
  : null;

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <React.Suspense fallback={<p role="status">正在打开工作台…</p>}>
      {ProjectOverview ? <ProjectOverview /> : <App />}
    </React.Suspense>
  </React.StrictMode>
);
