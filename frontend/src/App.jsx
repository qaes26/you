import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaPaste, FaDownload, FaMusic, FaVideo } from 'react-icons/fa';
import { getVideoInfo, getDownloadUrl } from './api';
import Footer from './Footer';

function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [videoInfo, setVideoInfo] = useState(null);
  const [error, setError] = useState(null);

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setUrl(text);
    } catch (err) {
      console.error('Failed to read clipboard', err);
    }
  };

  const fetchInfo = async () => {
    if (!url) return;
    setLoading(true);
    setError(null);
    setVideoInfo(null);
    try {
      const data = await getVideoInfo(url);
      setVideoInfo(data);
    } catch (err) {
      console.error(err);
      setError(err.detail || 'Failed to fetch video info. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (formatId) => {
    const link = getDownloadUrl(url, formatId);
    window.open(link, '_blank');
  };

  return (
    <div className="container" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card"
        >
          <h1 className="title">YouTube Downloader</h1>
          <p className="subtitle">Premium Quality Tool</p>

          <div className="input-group">
            <input
              type="text"
              className="url-input"
              placeholder="Paste YouTube Link here..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchInfo()}
            />
            <button className="paste-btn" onClick={url ? fetchInfo : handlePaste}>
              {url ? 'Go' : <><FaPaste /> Paste</>}
            </button>
          </div>

          {loading && <div className="spinner"></div>}

          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="error-msg"
            >
              {error}
            </motion.div>
          )}

          <AnimatePresence>
            {videoInfo && !loading && (
              <motion.div
                className="video-card"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
              >
                <div className="thumbnail">
                  <img src={videoInfo.thumbnail} alt={videoInfo.title} />
                </div>
                <div className="video-info">
                  <h2>{videoInfo.title}</h2>
                  <div className="formats-list">
                    {videoInfo.formats.map((fmt) => (
                      <div key={fmt.format_id} className="format-item">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          {fmt.type === 'audio' ? <FaMusic color="#00f2ea" /> : <FaVideo color="#ff0050" />}
                          <span>{fmt.label}</span>
                        </div>
                        <button
                          className="download-link"
                          onClick={() => handleDownload(fmt.format_id)}
                        >
                          <FaDownload /> Download
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
      <Footer />
    </div>
  );
}

export default App;
