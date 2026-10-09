import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import HomePage from './pages/HomePage';

// Code split: il chunk musicxml-player si carica solo su /score.
const UploadPage = lazy(() => import('./pages/UploadPage'));
const ScorePage = lazy(() => import('./pages/ScorePage'));

function App() {
  return (
    <Router>
      <div className="app-wrapper">
        <header className="container">
          <nav className="top-nav">
            <Link to="/" className="nav-logo logo-text">
              Cadenza
            </Link>
            <div className="nav-links">
              <Link to="/">Home</Link>
              <Link to="/upload">Upload Score</Link>
            </div>
          </nav>
        </header>

        <main>
          <Suspense fallback={<div className="route-loading">Loading…</div>}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/score" element={<ScorePage />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </Router>
  );
}

export default App;
