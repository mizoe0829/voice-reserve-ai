import { useState, useEffect, useRef, useCallback } from 'react';

interface UseSpeechRecognitionProps {
  onResult: (text: string) => void;
  silenceTimeoutMs?: number; // 無音判定までの時間（ミリ秒）
}

export function useSpeechRecognition({
  onResult,
  silenceTimeoutMs = 1800, // デフォルト 1.8秒のゆったり無音タイマー
}: UseSpeechRecognitionProps) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(false);
  
  const recognitionRef = useRef<any>(null);
  const accumulatedTextRef = useRef<string>('');
  const silenceTimerRef = useRef<any>(null);
  const onResultRef = useRef(onResult);

  // コールバック参照を最新に保つ
  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  // 発話を確定して送信する処理
  const finalizeSpeech = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }

    const finalText = accumulatedTextRef.current.trim();
    if (finalText) {
      onResultRef.current(finalText);
    }

    accumulatedTextRef.current = '';
    setTranscript('');

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        // すでに停止している場合のエラーを無視
      }
    }
    setIsListening(false);
  }, []);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      setIsSupported(true);
      const recognition = new SpeechRecognition();
      
      // ★ continuous = true にして途切れさせない！
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'ja-JP';

      recognition.onresult = (event: any) => {
        // 何か喋ったら既存の無音タイマーをリセット
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
        }

        let interimText = '';
        let newFinalText = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            newFinalText += event.results[i][0].transcript;
          } else {
            interimText += event.results[i][0].transcript;
          }
        }

        if (newFinalText) {
          accumulatedTextRef.current += newFinalText;
        }

        const currentDisplay = (accumulatedTextRef.current + interimText).trim();
        setTranscript(currentDisplay);

        // ★ ユーザーが話し終えて無音が続いた場合に発火するタイマー
        if (currentDisplay) {
          silenceTimerRef.current = setTimeout(() => {
            finalizeSpeech();
          }, silenceTimeoutMs);
        }
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        if (event.error !== 'no-speech') {
          finalizeSpeech();
        }
      };

      recognition.onend = () => {
        // ブラウザ側で勝手に終わった場合も、テキストがあれば確定
        if (accumulatedTextRef.current.trim()) {
          finalizeSpeech();
        } else {
          setIsListening(false);
        }
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }
    };
  }, [finalizeSpeech, silenceTimeoutMs]);

  const startListening = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      try {
        accumulatedTextRef.current = '';
        setTranscript('');
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.error('Error starting speech recognition:', err);
      }
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    // 手動でマイク停止ボタンを押した場合は即座に送信
    finalizeSpeech();
  }, [finalizeSpeech]);

  return {
    isListening,
    transcript,
    isSupported,
    startListening,
    stopListening,
  };
}
