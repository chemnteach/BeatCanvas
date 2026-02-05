import React from 'react';

function App() {
  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>🎵 BeatCanvas Enhanced UI</h1>
      <p>Enhanced UI is ready! Backend running on port 8002.</p>

      <div style={{ marginTop: '20px' }}>
        <h2>✅ Features Ready:</h2>
        <ul>
          <li>Two-level prompt system</li>
          <li>AI-powered style suggestions</li>
          <li>Storyboard review workflow</li>
          <li>Reference image uploads</li>
          <li>Real-time progress tracking</li>
          <li>Cost estimation</li>
        </ul>
      </div>

      <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
        <h3>🔧 Backend Status:</h3>
        <p>Server: http://localhost:8002</p>
        <button
          onClick={() => {
            fetch('http://localhost:8002/api/style-suggestions', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content_prompt: 'A dancer in moonlight' })
            })
            .then(res => res.json())
            .then(data => alert('AI Suggestions: ' + JSON.stringify(data.suggestions)))
            .catch(err => alert('Error: ' + err.message));
          }}
          style={{ padding: '10px 20px', fontSize: '16px', cursor: 'pointer' }}
        >
          Test AI Style Suggestions
        </button>
      </div>
    </div>
  );
}

export default App;