import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileMusic, CheckCircle2 } from 'lucide-react';
import { useMidi } from '../hooks/useMidi';
import MidiPanel from '../components/MidiPanel';
import './UploadPage.css';

const UploadPage: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const midi = useMidi();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const handleFileSelection = (file: File) => {
    setSelectedFile(file);
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const handleOpenScore = () => {
    if (selectedFile) {
      navigate('/score', {
        state: {
          file: selectedFile,
          midiEnabled: midi.isEnabled,
          midiInputId: midi.selectedInput?.id || null,
        },
      });
    }
  };

  return (
    <div className="upload-page container">
      <div className="upload-header">
        <h1 className="heading title">Upload Score</h1>
        <p className="subtitle">Upload your MusicXML file</p>
      </div>

      <div
        className={`upload-dropzone ${isDragging ? 'dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInput}
          accept=".xml,.musicxml,.mxl"
          className="hidden-input"
        />

        {!selectedFile ? (
          <div className="dropzone-content">
            <div className="icon-wrapper">
              <UploadCloud size={48} strokeWidth={1} />
            </div>
            <h2 className="heading dropzone-title">Drag & Drop Score</h2>
            <p className="dropzone-text">or <button className="browse-btn" onClick={triggerFileInput}>browse your computer</button></p>
            <p className="validation-text">Supported formats: .xml, .musicxml, .mxl</p>
          </div>
        ) : (
          <div className="success-content">
            <div className="icon-wrapper success">
              <CheckCircle2 size={48} strokeWidth={1} />
            </div>
            <h2 className="heading dropzone-title">Score Ready</h2>
            <div className="file-info">
              <FileMusic size={20} className="file-icon" />
              <span>{selectedFile.name}</span>
            </div>
            <div className="actions">
              <button className="btn btn-primary" onClick={handleOpenScore}>Open Score</button>
              <button className="btn btn-outline" onClick={() => setSelectedFile(null)}>Upload Another</button>
            </div>
          </div>
        )}
      </div>

      {/* MIDI Input Panel — connect your digital piano */}
      <MidiPanel midi={midi} />
    </div>
  );
};

export default UploadPage;
