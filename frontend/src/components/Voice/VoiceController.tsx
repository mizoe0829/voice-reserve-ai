import React, { useState } from 'react';
import { Mic, MicOff, Send, Volume2, Sparkles, Loader2 } from 'lucide-react';
import { WaveformVisualizer } from './WaveformVisualizer';

interface VoiceControllerProps {
  isListening: boolean;
  isSpeaking: boolean;
  isLoading: boolean;
  onStartListening: () => void;
  onStopListening: () => void;
  onSendMessage: (text: string) => void;
  transcript: string;
}

export const VoiceController: React.FC<VoiceControllerProps> = ({
  isListening,
  isSpeaking,
  isLoading,
  onStartListening,
  onStopListening,
  onSendMessage,
  transcript,
}) => {
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim()) {
      onSendMessage(inputText.trim());
      setInputText('');
    }
  };

  return (
    <div className="flex flex-col items-center gap-4 w-full max-w-lg mx-auto bg-slate-900/90 p-6 rounded-2xl border border-slate-800 shadow-2xl backdrop-blur-md">
      {/* 状態ステータステキスト */}
      <div className="flex items-center gap-2 text-sm font-semibold">
        {isLoading ? (
          <span className="text-amber-400 flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            AIが空き枠を確認しています...
          </span>
        ) : isSpeaking ? (
          <span className="text-orange-400 flex items-center gap-2">
            <Volume2 className="w-4 h-4 animate-bounce" />
            店員AIがお答えしています...
          </span>
        ) : isListening ? (
          <span className="text-red-400 flex items-center gap-2">
            <Sparkles className="w-4 h-4 animate-spin" />
            お話しください（聞き取り中...）
          </span>
        ) : (
          <span className="text-slate-400">マイクボタンを押して電話感覚でお話しください</span>
        )}
      </div>

      {/* 音声波形ビジュアライザ */}
      <WaveformVisualizer isActive={isListening || isSpeaking} />

      {/* リアルタイム音声認識テキスト表示 */}
      {transcript && isListening && (
        <div className="w-full text-center px-4 py-2 bg-slate-950/70 rounded-xl border border-slate-800 text-sm text-slate-200 italic">
          「{transcript}」
        </div>
      )}

      {/* 巨大マイクボタン */}
      <div className="relative my-2">
        {isListening && (
          <div className="absolute inset-0 rounded-full bg-orange-500 animate-pulse-ring" />
        )}
        <button
          onClick={isListening ? onStopListening : onStartListening}
          disabled={isLoading}
          className={`relative z-10 w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-xl active:scale-95 ${
            isListening
              ? 'bg-red-500 text-white hover:bg-red-600 shadow-red-500/40'
              : 'bg-gradient-to-tr from-orange-600 to-amber-500 text-white hover:from-orange-500 hover:to-amber-400 shadow-orange-500/30'
          }`}
          title={isListening ? 'マイクを停止' : '話しかける'}
        >
          {isListening ? (
            <MicOff className="w-8 h-8 animate-pulse" />
          ) : (
            <Mic className="w-8 h-8" />
          )}
        </button>
      </div>

      {/* 手動入力フォールバック（キーボード入力用） */}
      <form onSubmit={handleSubmit} className="w-full flex items-center gap-2 mt-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="またはメッセージを入力...（例: 金曜夜7時、3名で）"
          className="flex-1 bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-orange-500 transition-colors"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || isLoading}
          className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-orange-400 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
