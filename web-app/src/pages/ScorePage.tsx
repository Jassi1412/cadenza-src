import { useEffect, useRef, useState, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useMidi } from '../hooks/useMidi';
import { useVerdict } from '../hooks/useVerdict';
import PlaybackBar from '../components/PlaybackBar';
import './ScorePage.css';

// Riferimenti modul-level per gli import dinamici.
let Player: any = null;
let OpenSheetMusicDisplayRenderer: any = null;
let VerovioConverter: any = null;

/** BPM iniziali se lo spartito non dichiara un tempo. */
const BPM_FALLBACK = 120;

/** BPM: prima <sound tempo>, poi <per-minute>, altrimenti fallback. */
function readScoreBpm(scoreXml: string): number {
  const sound = /<sound\b[^>]*\btempo="([^"]+)"/.exec(scoreXml);
  if (sound) {
    const bpm = Number(sound[1]);
    if (Number.isFinite(bpm) && bpm > 0) return Math.round(bpm);
  }
  const perMinute = /<per-minute>([^<]+)<\/per-minute>/.exec(scoreXml);
  if (perMinute) {
    const bpm = Number(perMinute[1]);
    if (Number.isFinite(bpm) && bpm > 0) return Math.round(bpm);
  }
  return BPM_FALLBACK;
}

/** Fasi: idle/countdown/playing; la fine si deduce da position>=duration. */
type Phase = 'idle' | 'countdown' | 'playing';

/** Margine: il player blocca position a duration-1. */
const END_SLACK_MS = 2;

/** Sequencer fermo: meglio chiudere che restare aperti. */
const STALL_MS = 2000;

/** Silenzio fra un numero e l'altro del countdown, in ms. */
const COUNTDOWN_STEP_MS = 750;

const ScorePage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<any>(null);
  const osmdRef = useRef<any>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState('Preparing the score...');
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<Phase>('idle');
  const [count, setCount] = useState(3);
  // Tempo utente e tempo scritto, per ricavare il fattore.
  const [scoreBpm, setScoreBpm] = useState(BPM_FALLBACK);
  const [bpm, setBpm] = useState(BPM_FALLBACK);

  const file = location.state?.file as File | undefined;
  const midiEnabled = location.state?.midiEnabled as boolean | undefined;
  const midiInputId = location.state?.midiInputId as string | undefined;

  const midi = useMidi();

  const verdict = useVerdict(midi.recording);
  const runAnalysis = useCallback(async () => {
    if (!file) return;
    try {
      const scoreXml = await file.text();
      await verdict.analyse(scoreXml, scoreBpm / bpm);
    } catch (err) {
      console.error('[ScorePage] Non sono riuscito a leggere lo spartito:', err);
    }
  }, [file, verdict, scoreBpm, bpm]);


  const verdictPanelRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (verdict.status === 'done') {
      verdictPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [verdict.status]);

  useEffect(() => {
    if (midiEnabled && !midi.isEnabled) {
      midi.enable().then(() => {
        if (midiInputId) {
          // Attendi un tick: gli input si popolano dopo.
          setTimeout(() => midi.selectInput(midiInputId), 200);
        }
      });
    }
  }, [midiEnabled, midiInputId]); // eslint-disable-line react-hooks/exhaustive-deps

/** Fine prova: spartito fermo, verdetto automatico. */
  const finishPlayAlong = useCallback(async () => {
    setPhase('idle');
    setIsPlaying(false);
    setProgress(100);
    playerRef.current?.pause();
    await runAnalysis();
  }, [runAnalysis]);

/** Inizia: countdown, poi suona e registra. */
  const handlePlayAlong = useCallback(async () => {
    const player = playerRef.current;
    if (!player || isLoading) return;
    if (!midi.isEnabled) {
      await midi.enable();
      // Senza questa attesa i primi eventi della prova andrebbero persi.
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
    player.pause();
    player.rewind();
    midi.clearRecording();
    setProgress(0);
    setCount(3);
    setPhase('countdown');
  }, [isLoading, midi]);

/** Countdown: tempo di posizionare le mani. */
  useEffect(() => {
    if (phase !== 'countdown') return;
    if (count > 0) {
      const timer = setTimeout(() => setCount((c) => c - 1), COUNTDOWN_STEP_MS);
      return () => clearTimeout(timer);
    }
    playerRef.current?.play();
    setIsPlaying(true);
    setPhase('playing');
  }, [phase, count]);

// Fine dedotta da position>=duration, con soglia sul tetto reale.
  useEffect(() => {
    if (phase === 'countdown') return;
    if (phase === 'idle' && !isPlaying) return;
    let animationId: number;
    let lastPos = -1;
    let stalledSince = 0;
    const tick = (now: number) => {
      const player = playerRef.current;
      if (player) {
        const dur = player.duration;
        const pos = player.position;
        if (dur > 0) {
          setProgress((pos / dur) * 100);
          if (phase === 'playing') {
            if (pos >= dur - END_SLACK_MS) {
              void finishPlayAlong();
              return;
            }
// Sequencer fermo: chiudi la prova.
            if (pos === lastPos) {
              if (stalledSince === 0) stalledSince = now;
              else if (now - stalledSince > STALL_MS) {
                void finishPlayAlong();
                return;
              }
            } else {
              lastPos = pos;
              stalledSince = 0;
            }
          }
        }
      }
      animationId = requestAnimationFrame(tick);
    };
    animationId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationId);
  }, [phase, isPlaying, finishPlayAlong]);

  useEffect(() => {
    if (!file) {
      navigate('/upload');
      return;
    }

    let destroyed = false;

    const initPlayer = async () => {
      try {
        setLoadingMessage('Loading the music engine...');

        const lib = await import('@music-i18n/musicxml-player');
        Player = lib.Player;
        OpenSheetMusicDisplayRenderer = lib.OpenSheetMusicDisplayRenderer;
        VerovioConverter = lib.VerovioConverter;

        if (destroyed) return;

        setLoadingMessage('Reading the score file...');

        const arrayBuffer = await file.arrayBuffer();

        if (destroyed) return;

        setLoadingMessage('Rendering the notation...');

        const renderer = new OpenSheetMusicDisplayRenderer(
          {
            backend: 'svg',
            followCursor: true,
            drawCredits: true,
            drawTitle: true,
            drawComposer: true,
            drawPartNames: true,
            cursorsOptions: [
              {
                type: 0,
                color: '#C5A880',
                alpha: 0.6,
                follow: true,
              },
            ],
          }
        );

        // Bravura evita errori di caricamento del font Leipzig.
        const converter = new VerovioConverter({
          font: 'Bravura'
        });

        // Il tempo scritto imposta lo slider iniziale.
        const written = readScoreBpm(await file.text());
        setScoreBpm(written);
        setBpm(written);

        const player = await Player.create({
          musicXml: arrayBuffer,
          container: containerRef.current!,
          renderer,
          converter,
          followCursor: true,
          velocity: 1,
          repeat: 1,
        });

        if (destroyed) {
          player.destroy();
          return;
        }

        playerRef.current = player;

        console.log('[ScorePage] Renderer keys:', Object.keys(renderer));
        const osmd = (renderer as any).osmd || (renderer as any)._osmd;
        if (osmd) {
          osmdRef.current = osmd;
          console.log('[ScorePage] OSMD instance acquired. Cursors:', osmd.cursors?.length ?? 0);

          // Nessun override manuale: ci si affida a OSMD col font SMuFL.
          if (osmd.cursors?.length > 0) {
            osmd.cursors[0].hide();
          }
        } else {
          console.warn('[ScorePage] OSMD instance not found on renderer._osmd');
        }

        setIsLoading(false);
      } catch (err: any) {
        console.error('Player initialization error:', err);
        if (!destroyed) {
          setError(err.message || 'Failed to load the score. Please try another file.');
          setIsLoading(false);
        }
      }
    };

    initPlayer();

    return () => {
      destroyed = true;
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
      osmdRef.current = null;
    };
  }, [file, navigate]);

/** Slider scala solo la velocità; il fattore va al servizio una volta. */
  useEffect(() => {
    if (phase === 'playing' || phase === 'countdown') return;
    const player = playerRef.current;
    if (player) player.velocity = bpm / scoreBpm;
  }, [bpm, scoreBpm, phase]);

  const handlePlayPause = useCallback(() => {
    const player = playerRef.current;
    if (!player || phase === 'countdown' || phase === 'playing') return;
    if (isPlaying) {
      player.pause();
      setIsPlaying(false);
    } else {
      player.play();
      setIsPlaying(true);
    }
  }, [isPlaying, phase]);

  // Stop interrompe anche la prova; la registrazione resta per riascolto.
  const handleStop = useCallback(() => {
    const player = playerRef.current;
    if (!player) return;
    player.pause();
    player.rewind();
    setProgress(0);
    setIsPlaying(false);
    setPhase('idle');
  }, []);

  // Spazio = play/pause, fuori da countdown/prova.
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === ' ' && !isLoading && phase !== 'countdown' && phase !== 'playing') {
        e.preventDefault();
        handlePlayPause();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlePlayPause, isLoading, phase]);

  if (error) {
    return (
      <div className="score-page container">
        <div className="score-error">
          <h2 className="heading">Unable to Load Score</h2>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => navigate('/upload')}>
            <ArrowLeft size={18} /> Try Another File
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="score-page">
      {/* Header: back + stato della prova */}
      <div className="score-header container">
        <button className="back-btn" onClick={() => navigate('/upload')}>
          <ArrowLeft size={20} />
        </button>

        {(phase === 'countdown' || phase === 'playing') && (
          <div className="practice-status">
            <span className="practice-status-dot" />
            {phase === 'countdown' ? 'Pronti…' : 'Prova in corso'}
          </div>
        )}
      </div>

      <div className="score-container">
        {isLoading && (
          <div className="loading-overlay">
            <div className="loading-spinner" />
            <p className="loading-text">{loadingMessage}</p>
          </div>
        )}
        <div ref={containerRef} className="sheet-container" id="sheet-container" />

        {/* Countdown overlay: il musicista guarda le mani, non la pagina. */}
        {phase === 'countdown' && (
          <div className="countdown-overlay">
            <div className="countdown-value" key={count}>{count > 0 ? count : 'Via'}</div>
            <p className="countdown-hint">Preparati, si parte fra poco</p>
          </div>
        )}
      </div>

      {/* Verdetti: visibili solo dopo l'analisi */}
      {verdict.status !== 'idle' && (
        <section className="verdict-panel" ref={verdictPanelRef}>
          <div className="verdict-panel-head">
            <h2 className="heading">Il verdetto</h2>
            {verdict.status === 'done' && (
              <button className="btn btn-outline" onClick={verdict.reset}>Chiudi</button>
            )}
          </div>

          {verdict.status === 'working' && <p className="verdict-note">Allineamento e verifica delle sette regole…</p>}

          {verdict.status === 'error' && <p className="verdict-note verdict-error">{verdict.error}</p>}

          {verdict.status === 'done' && verdict.verdicts && (
            <>
              <p className="verdict-note">{verdict.noteCount} note analizzate</p>
              <ul className="verdict-list">
                {Object.entries(verdict.verdicts).map(([key, v]) => (
                  <li key={key} className={v.ok ? 'verdict-ok' : 'verdict-bad'}>
                    <span className="verdict-mark">{v.ok ? '✓' : '✗'}</span>
                    <span className="verdict-name">{key}</span>
                    <span className="verdict-detail">{v.ok ? 'conforme' : 'violata'}</span>
                  </li>
                ))}
              </ul>
              <button className="btn btn-outline verdict-retry" onClick={() => void handlePlayAlong()}>
                Suona di nuovo
              </button>
            </>
          )}
        </section>
      )}

      {!isLoading && (
        <PlaybackBar
          isPlaying={isPlaying}
          isTakeActive={phase === 'countdown' || phase === 'playing'}
          isLoading={isLoading}
          progress={progress}
          onPlayPause={handlePlayPause}
          onStop={handleStop}
          onPlayAlong={handlePlayAlong}
          bpm={bpm}
          scoreBpm={scoreBpm}
          onBpmChange={setBpm}
        />
      )}
    </div>
  );
};

export default ScorePage;
