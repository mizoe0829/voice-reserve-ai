import React from 'react';
import { Bot, User } from 'lucide-react';

export interface ChatMessage {
  sender: 'bot' | 'user';
  text: string;
  time: string;
}

interface TranscriptHistoryProps {
  messages: ChatMessage[];
}

export const TranscriptHistory: React.FC<TranscriptHistoryProps> = ({ messages }) => {
  return (
    <div className="flex flex-col bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-2xl backdrop-blur-md h-[480px]">
      <div className="pb-3 border-b border-slate-800 mb-3 flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-300">リアルタイム音声対話ログ</h3>
        <span className="text-[10px] text-slate-500">電話感覚の会話履歴</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3.5 pr-1">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 text-xs gap-2">
            <Bot className="w-8 h-8 text-slate-600 animate-pulse" />
            <span>マイクボタンを押して、「今週金曜の夜7時に4人で空いてる？」と話しかけてみてください。</span>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-2.5 ${
                msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
              }`}
            >
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                  msg.sender === 'user'
                    ? 'bg-orange-600 text-white'
                    : 'bg-slate-800 text-orange-400 border border-slate-700'
                }`}
              >
                {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed shadow-sm ${
                  msg.sender === 'user'
                    ? 'bg-orange-600 text-white rounded-tr-sm'
                    : 'bg-slate-800/90 border border-slate-700/60 text-slate-200 rounded-tl-sm'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
