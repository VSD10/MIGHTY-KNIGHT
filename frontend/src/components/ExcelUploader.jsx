import React, { useState } from 'react';
import { UploadCloud, CheckCircle, AlertTriangle, X, FileText, Download } from 'lucide-react';
import { uploadExcel, getDownloadTemplateUrl } from '../services/api';

export default function ExcelUploader({ isOpen, onClose, onUploadSuccess, summaryData }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setErrorMsg(null);
    try {
      const data = await uploadExcel(file);
      setResult(data);
      if (onUploadSuccess) onUploadSuccess(data);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to upload Excel file.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '620px', padding: '28px', position: 'relative' }}>
        <button
          onClick={onClose}
          style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer' }}
        >
          <X size={20} />
        </button>

        <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#fff', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <UploadCloud style={{ color: 'var(--accent-gold)' }} /> Upload Academy Master Data (.xlsx)
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Upload an Excel file containing <strong style={{ color: '#fff' }}>Students</strong> and <strong style={{ color: '#fff' }}>Coaches</strong> sheets.
        </p>

        {/* Download Format Option */}
        <div style={{
          background: 'var(--accent-gold-bg)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          padding: '12px 16px',
          borderRadius: 'var(--radius-md)',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-gold)', display: 'block' }}>
              Need the official Excel template format?
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Download pre-formatted sample workbook matching all BRD fields & 8 coaches.
            </span>
          </div>

          <a
            href={getDownloadTemplateUrl()}
            download="mighty_knight_template.xlsx"
            className="btn btn-secondary"
            style={{
              padding: '6px 14px',
              fontSize: '0.8rem',
              borderColor: 'var(--accent-gold)',
              color: 'var(--accent-gold)',
              textDecoration: 'none'
            }}
          >
            <Download size={14} /> Download Excel Format (.xlsx)
          </a>
        </div>

        {/* Current Active Data Banner */}
        {summaryData && (
          <div style={{ background: 'var(--bg-secondary)', padding: '14px', borderRadius: 'var(--radius-md)', marginBottom: '20px', display: 'flex', gap: '16px' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>ACTIVE STUDENTS</span>
              <p style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-gold)' }}>{summaryData.students_count || 0}</p>
            </div>
            <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: '16px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>ACTIVE COACHES</span>
              <p style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--status-success)' }}>{summaryData.coaches_count || 0}</p>
            </div>
          </div>
        )}

        {/* Drop zone */}
        <div style={{
          border: '2px dashed var(--border-light)',
          borderRadius: 'var(--radius-md)',
          padding: '30px',
          textAlign: 'center',
          background: 'rgba(255, 255, 255, 0.02)',
          marginBottom: '20px'
        }}>
          <input
            type="file"
            accept=".xlsx, .xls"
            onChange={handleFileChange}
            style={{ display: 'none' }}
            id="excel-file-input"
          />
          <label htmlFor="excel-file-input" style={{ cursor: 'pointer' }}>
            <FileText size={40} style={{ color: 'var(--accent-gold)', marginBottom: '10px' }} />
            <p style={{ fontSize: '0.95rem', fontWeight: 600, color: '#fff' }}>
              {file ? file.name : 'Click to select or drag .xlsx file here'}
            </p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Supports Students & Coaches sheets (Section 5 & 6)
            </p>
          </label>
        </div>

        {errorMsg && (
          <div style={{ padding: '12px', background: 'var(--status-danger-bg)', border: '1px solid var(--status-danger)', borderRadius: 'var(--radius-md)', color: '#ef4444', fontSize: '0.85rem', marginBottom: '16px' }}>
            {errorMsg}
          </div>
        )}

        {result && (
          <div style={{ padding: '14px', background: 'var(--status-success-bg)', border: '1px solid var(--status-success)', borderRadius: 'var(--radius-md)', marginBottom: '16px' }}>
            <p style={{ fontWeight: 700, color: 'var(--status-success)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle size={16} /> Excel Ingested Successfully!
            </p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-primary)', marginTop: '4px' }}>
              Parsed {result.total_students_parsed} students and {result.total_coaches_parsed} coaches.
            </p>
            {result.parsing_errors && result.parsing_errors.length > 0 && (
              <div style={{ marginTop: '8px', maxHeight: '100px', overflowY: 'auto', fontSize: '0.75rem', color: '#f59e0b' }}>
                <strong>Warnings/Errors ({result.parsing_errors.length}):</strong>
                {result.parsing_errors.map((e, idx) => (
                  <div key={idx}>• Sheet '{e.sheet}' row {e.row} ({e.column}): {e.message}</div>
                ))}
              </div>
            )}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button onClick={onClose} className="btn btn-secondary">Close</button>
          <button onClick={handleUpload} disabled={!file || uploading} className="btn btn-primary">
            {uploading ? 'Processing File...' : 'Upload & Recognize Data'}
          </button>
        </div>
      </div>
    </div>
  );
}
