import React from 'react';
import VideoGenerator from './components/VideoGenerator';
import Header from './components/Header';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-800 to-dark-900">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <VideoGenerator />
      </main>
    </div>
  );
}

export default App;