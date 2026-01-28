import React from 'react';

const Footer = () => {
    return (
        <div style={{
            marginTop: 'auto',
            padding: '20px',
            textAlign: 'center',
            width: '100%',
            background: 'rgba(0,0,0,0.5)',
            backdropFilter: 'blur(10px)',
            borderTop: '1px solid rgba(255,255,255,0.05)',
            fontSize: '0.9rem',
            color: '#888'
        }}>
            <p style={{ margin: 0 }}>
                Prepared by <span style={{ color: '#00f2ea', fontWeight: 'bold' }}>Qais Talal Al-Jazi</span>
            </p>
        </div>
    );
};

export default Footer;
