import { Piano, Plug, Unplug, ChevronDown, ChevronUp, Music } from 'lucide-react';
import type { UseMidiReturn } from '../hooks/useMidi';
import { useState } from 'react';
import './MidiPanel.css';

interface MidiPanelProps {
  midi: UseMidiReturn;
}

const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

const MidiPanel: React.FC<MidiPanelProps> = ({ midi }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!midi.isSupported) {
    return null; // Nascosto se Web MIDI non è supportato
  }

  return (
    <div className={`midi-panel ${isExpanded ? 'expanded' : ''}`}>
      <button
        className="midi-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="midi-toggle-left">
          <Piano size={18} />
          <span className="midi-label">MIDI Input</span>
          {midi.isEnabled && midi.selectedInput && (
            <span className="midi-device-badge">
              {midi.selectedInput.name}
            </span>
          )}
          {midi.isEnabled && midi.activeNotes.size > 0 && (
            <span className="midi-activity-dot" />
          )}
        </div>
        {isExpanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
      </button>

      {isExpanded && (
        <div className="midi-body">
          {!midi.isEnabled ? (
            <div className="midi-connect-section">
              <p className="midi-info">
                Connect your digital piano or MIDI keyboard to play along with the score.
              </p>
              <button className="btn btn-primary midi-enable-btn" onClick={midi.enable}>
                <Plug size={16} /> Enable MIDI
              </button>
              {midi.error && (
                <p className="midi-error">{midi.error}</p>
              )}
            </div>
          ) : (
            <div className="midi-connected-section">
              <div className="midi-row">
                <span className="midi-row-label">Device</span>
                {midi.inputs.length === 0 ? (
                  <span className="midi-no-device">No MIDI device detected</span>
                ) : (
                  <select
                    className="midi-select"
                    value={midi.selectedInput?.id || ''}
                    onChange={(e) => midi.selectInput(e.target.value)}
                  >
                    {midi.inputs.map((input) => (
                      <option key={input.id} value={input.id}>
                        {input.manufacturer ? `${input.manufacturer} — ` : ''}{input.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="midi-row">
                <span className="midi-row-label">Active Notes</span>
                <div className="midi-notes-display">
                  {midi.activeNotes.size === 0 ? (
                    <span className="midi-waiting">
                      <Music size={14} /> Waiting for input...
                    </span>
                  ) : (
                    <div className="midi-active-notes">
                      {Array.from(midi.activeNotes.values()).map((note) => (
                        <span key={note.number} className="midi-note-chip">
                          {note.identifier}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="midi-keyboard-visual">
                {Array.from({ length: 24 }, (_, i) => {
                  const noteIndex = i % 12;
                  const isBlack = [1, 3, 6, 8, 10].includes(noteIndex);
                  const midiNumber = 48 + i; // C3–B4
                  const isActive = midi.activeNotes.has(midiNumber);
                  return (
                    <div
                      key={i}
                      className={`mini-key ${isBlack ? 'black' : 'white'} ${isActive ? 'active' : ''}`}
                      title={`${NOTE_NAMES[noteIndex]}${Math.floor((48 + i) / 12) - 1}`}
                    />
                  );
                })}
              </div>

              <button className="midi-disconnect-btn" onClick={midi.disable}>
                <Unplug size={14} /> Disconnect
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MidiPanel;
