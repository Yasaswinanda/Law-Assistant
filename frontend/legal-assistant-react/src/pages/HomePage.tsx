import React from 'react';
import { Layout } from '../components/Layout';

export const HomePage: React.FC = () => {
  return (
    <Layout currentPage="home">
      <section className="hero">
        <div className="card">
          <h1 style={{ margin: '0 0 8px 0' }}>Get legal help without the hassle</h1>
          <p className="muted">
            Ask questions to the built‑in AI, find a nearby lawyer, and keep all your conversations in one clean place. 
            No tech knobs. No jargon. Just answers.
          </p>
          <div className="spacer"></div>
          <div className="row">
            <a className="btn prime" href="/auth">Get Started</a>
            <a className="btn" href="/auth?mode=signup">I'm new here</a>
          </div>
          <div className="spacer"></div>
          <div className="row">
            <span className="pill">Secure accounts</span>
            <span className="pill">Chat with real lawyers</span>
            <span className="pill">Upload PDFs</span>
            <span className="pill">Location‑aware search</span>
          </div>
        </div>
        <div className="grid">
          <div className="card">
            <h3 style={{ margin: '0 0 6px 0' }}>How it works</h3>
            <div className="divider"></div>
            <ol>
              <li>Sign up as a <b>Client</b> or <b>Lawyer</b>.</li>
              <li>Clients can search for lawyers nearby and start a chat.</li>
              <li>Use the AI Assistant to summarize documents or draft questions.</li>
              <li>Everything stays tidy and easy to find.</li>
            </ol>
          </div>
          <div className="card">
            <h3 style={{ margin: '0 0 6px 0' }}>Privacy first</h3>
            <div className="divider"></div>
            <p className="muted">
              You control your data. Tokens are stored locally on your device and sent securely for each request.
            </p>
          </div>
        </div>
      </section>
    </Layout>
  );
};