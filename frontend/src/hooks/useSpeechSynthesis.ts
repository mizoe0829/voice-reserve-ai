import { useState, useCallback } from 'react';

export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);

  const speak = useCallback((text: string, onEnd?: () => void) => {
    if (!('speechSynthesis' in window)) {
      if (onEnd) onEnd();
      return;
    }

    // 再生中の音声を一度キャンセル
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ja-JP';
    utterance.rate = 1.05; // わずかに軽快で聞き取りやすい速度
    utterance.pitch = 1.1; // 明るく丁寧な店員トーン

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      if (onEnd) onEnd();
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      if (onEnd) onEnd();
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  const stop = useCallback(() => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  return {
    speak,
    stop,
    isSpeaking,
  };
}
