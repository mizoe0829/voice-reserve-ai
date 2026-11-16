import { useState, useEffect } from 'react';
import { VoiceController } from './components/Voice/VoiceController';
import { LiveReservationCard, SlotState } from './components/Reservation/LiveReservationCard';
import { TranscriptHistory, ChatMessage } from './components/Chat/TranscriptHistory';
import { BookingCalendar } from './components/Admin/BookingCalendar';
import { useSpeechRecognition } from './hooks/useSpeechRecognition';
import { useSpeechSynthesis } from './hooks/useSpeechSynthesis';
import { Sparkles, UtensilsCrossed, CalendarDays, RotateCcw } from 'lucide-react';

interface ShopInfo {
  id: number;
  name: string;
  industry_type: string;
  address: string;
  open_time: string;
  close_time: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'voice' | 'admin'>('voice');
  const [shopInfo, setShopInfo] = useState<ShopInfo | null>(null);

  // 初回マウント時に店舗マスタ情報を取得
  useEffect(() => {
    fetch('/api/shop')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.name) {
          setShopInfo(data);
        }
      })
      .catch((err) => console.error('Failed to load shop info:', err));
  }, []);

  // スロット状態 ＆ 会話ステージ
  const [slots, setSlots] = useState<SlotState>({
    date: null,
    time: null,
    guests: null,
    seat_type: 'table',
    course_name: null,
    customer_name: null,
    phone_number: null,
    allergies: [],
    pre_orders: [],
    special_requests: null,
  });
  const [stage, setStage] = useState<string>('hearing');
  const [bookingCode, setBookingCode] = useState<string | null>(null);
  const [isSlotAvailable, setIsSlotAvailable] = useState<boolean>(true);
  const [alternativeSlots, setAlternativeSlots] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // 音声合成（読み上げ）フック
  const { speak, stop: stopSpeaking, isSpeaking } = useSpeechSynthesis();

  // メッセージ送信（API通信）
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    // ユーザー発話をチャットに追加
    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages((prev) => [...prev, { sender: 'user', text, time: nowStr }]);
    setIsLoading(true);

    try {
      const response = await fetch('/api/dialogue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: bookingCode,
          current_slots: slots,
          stage: stage,
        }),
      });

      const data = await response.json();
      setIsLoading(false);

      // スロットとステージの更新
      if (data.updated_slots) {
        setSlots(data.updated_slots);
      }
      if (data.stage) {
        setStage(data.stage);
      }
      if (data.booking_code) {
        setBookingCode(data.booking_code);
      }
      if (data.is_slot_available !== undefined) {
        setIsSlotAvailable(data.is_slot_available);
      }
      if (data.alternative_slots) {
        setAlternativeSlots(data.alternative_slots);
      }

      // ボットの返答をチャットに追加
      const botTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setMessages((prev) => [...prev, { sender: 'bot', text: data.reply_text, time: botTime }]);

      // 音声読み上げ
      speak(data.reply_text);
    } catch (err) {
      console.error('Dialogue API error:', err);
      setIsLoading(false);
    }
  };

  // 音声認識フック
  const { isListening, transcript, startListening, stopListening } = useSpeechRecognition({
    onResult: (finalText) => {
      handleSendMessage(finalText);
    },
  });

  // 予約リセット
  const handleReset = () => {
    stopSpeaking();
    stopListening();
    setSlots({
      date: null,
      time: null,
      guests: null,
      seat_type: 'table',
      course_name: null,
      customer_name: null,
      phone_number: null,
      allergies: [],
      pre_orders: [],
      special_requests: null,
    });
    setStage('hearing');
    setBookingCode(null);
    setIsSlotAvailable(true);
    setAlternativeSlots([]);
    setMessages([]);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* ナビゲーションバー */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-gradient-to-br from-orange-500 to-amber-600 rounded-xl shadow-lg shadow-orange-600/20">
              <UtensilsCrossed className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-black tracking-tight text-slate-100 flex items-center gap-2">
                VoiceReserve AI
                {shopInfo && (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-orange-950/80 text-orange-300 border border-orange-800/60 font-sans">
                    {shopInfo.name}
                  </span>
                )}
              </h1>
              <p className="text-[10px] text-orange-400 font-semibold uppercase tracking-wider">
                問い合わせ不要！音声ダイレクト予約ボット
              </p>
            </div>
          </div>

          {/* タブ切り替え */}
          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1 bg-slate-950/80 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setActiveTab('voice')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeTab === 'voice'
                    ? 'bg-orange-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" /> 音声予約画面
              </button>
              <button
                onClick={() => setActiveTab('admin')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeTab === 'admin'
                    ? 'bg-orange-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <CalendarDays className="w-3.5 h-3.5" /> 予約台帳 ＆ 厨房伝票
              </button>
            </nav>

            {activeTab === 'voice' && (
              <button
                onClick={handleReset}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold flex items-center gap-1 transition-colors"
                title="新しい予約を始める"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
        {activeTab === 'voice' ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* 左側: 音声コントローラー ＆ 対話ログ (6カラム) */}
            <div className="lg:col-span-6 flex flex-col gap-6">
              {/* マイク・音声コントローラー */}
              <VoiceController
                isListening={isListening}
                isSpeaking={isSpeaking}
                isLoading={isLoading}
                onStartListening={startListening}
                onStopListening={stopListening}
                onSendMessage={handleSendMessage}
                transcript={transcript}
              />

              {/* 会話履歴ログ */}
              <TranscriptHistory messages={messages} />
            </div>

            {/* 右側: リアルタイム予約プレビューカード (6カラム) */}
            <div className="lg:col-span-6">
              <LiveReservationCard
                slots={slots}
                stage={stage}
                bookingCode={bookingCode}
                shopName={shopInfo?.name}
                isSlotAvailable={isSlotAvailable}
                alternativeSlots={alternativeSlots}
                onSelectAlternativeSlot={(alt) => {
                  handleSendMessage(`じゃあ${alt}でお願いします`);
                }}
              />
            </div>
          </div>
        ) : (
          <BookingCalendar />
        )}
      </main>
    </div>
  );
}
