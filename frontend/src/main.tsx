import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { initializeWorkspace } from './api';
import '@fontsource-variable/roboto/wght.css';
import './styles.css';
const root=ReactDOM.createRoot(document.getElementById('root')!);
initializeWorkspace().then(()=>root.render(<React.StrictMode><App /></React.StrictMode>)).catch(()=>root.render(<main><h1>Workspace unavailable</h1><p>The free service may be starting or busy. Please try again shortly.</p><button onClick={()=>location.reload()}>Retry</button></main>));
