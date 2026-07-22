import { useState, useRef, useEffect } from 'react';
import axios from 'axios';

export default function StoreDeskTest() {
  const [sessionId, setSessionId] = useState('');
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [conversation, setConversation] = useState([]);
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [connectorId, setConnectorId] = useState('test-connector-123');
  const [isLoading, setIsLoading] = useState(false);
  const [debugRequest, setDebugRequest] = useState(null);
  const [debugResponse, setDebugResponse] = useState(null);
  const [pendingConfirmation, setPendingConfirmation] = useState(false);
  const [mockScenario, setMockScenario] = useState('happy_path');
  const [isClient, setIsClient] = useState(false);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingStartedAtRef = useRef(0);
  const isStoppingRef = useRef(false);

  // Generate UUID only on client side to prevent hydration mismatch
  useEffect(() => {
    setIsClient(true);
    setSessionId(generateUUID());
  }, []);

  const testProducts = [
    { id: '7626ff3a-1234-5678-9abc-123456789abc', name: 'Product 1' },
    { id: '78561ba7-2345-6789-abcd-23456789abcd', name: 'Product 2' },
    { id: '89012def-3456-789a-bcde-3456789abcde', name: 'Product 3' },
    { id: 'f3456789-4567-89ab-cdef-456789abcdef', name: 'Product 4' },
    { id: 'a456789b-5678-9abc-def0-56789abcdef0', name: 'Product 5' }
  ];

  const testPrompts = {
    'Stock Monitoring': [
      'Enable quantity monitoring for selected products with threshold 5',
      'Disable stock monitoring for all products',
      'Set stock alert to 10 units for selected products',
      'Turn off quantity monitoring for selected products'
    ],
    'Price Monitoring': [
      'Enable price margin monitoring at 8 percent for selected products',
      'Disable price monitoring for all products',
      'Set price threshold to 5 percent for selected products'
    ],
    'Combined': [
      'Enable both stock and price monitoring for selected products',
      'Disable all monitoring for selected products',
      'Set stock threshold to 3 and price margin to 10 percent for selected products'
    ],
    'Confirmation Flow': [
      'Disable price monitoring for all products',
      'Yes proceed',
      'Cancel'
    ],
    'Edge Cases': [
      'Enable monitoring',
      'Set threshold to 5',
      'Yes'
    ]
  };

  function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  const cleanupMediaStream = (recorder) => {
    try {
      recorder?.stream?.getTracks?.().forEach((track) => track.stop());
    } catch (_) {
      // ignore
    }
  };

  const startRecording = async () => {
    if (isRecording || mediaRecorderRef.current?.state === 'recording') {
      return;
    }
    isStoppingRef.current = false;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: 1,
        },
      });
      // Prefer webm/opus when available (Chrome/Firefox); fall back to browser default.
      const preferredType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : '';
      const recorder = preferredType
        ? new MediaRecorder(stream, { mimeType: preferredType })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error || event);
        cleanupMediaStream(recorder);
        mediaRecorderRef.current = null;
        setIsRecording(false);
        isStoppingRef.current = false;
        alert('Recording failed. Please try again.');
      };

      recorder.onstop = async () => {
        cleanupMediaStream(recorder);
        const mimeType = recorder.mimeType || 'audio/webm';
        const chunks = audioChunksRef.current;
        audioChunksRef.current = [];
        mediaRecorderRef.current = null;
        isStoppingRef.current = false;

        const audioBlob = new Blob(chunks, { type: mimeType });
        const elapsedMs = Date.now() - recordingStartedAtRef.current;

        // Only reject truly empty captures — short "yes"/"no" replies are valid.
        if (!chunks.length || audioBlob.size === 0) {
          alert('No audio captured. Click Start Voice, speak, then click Stop Voice.');
          return;
        }
        if (elapsedMs < 350) {
          alert('Recording was too short. Speak, then click Stop Voice.');
          return;
        }

        const audioBase64 = await blobToBase64(audioBlob);
        submitRequest(audioBase64, 'audio');
      };

      // Final chunk is emitted automatically on stop() — do not call requestData().
      recorder.start();
      recordingStartedAtRef.current = Date.now();
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Could not access microphone');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || isStoppingRef.current) {
      return;
    }
    if (recorder.state === 'inactive') {
      cleanupMediaStream(recorder);
      mediaRecorderRef.current = null;
      setIsRecording(false);
      return;
    }
    isStoppingRef.current = true;
    setIsRecording(false);
    try {
      recorder.stop();
    } catch (error) {
      console.error('Error stopping recording:', error);
      cleanupMediaStream(recorder);
      mediaRecorderRef.current = null;
      isStoppingRef.current = false;
    }
  };

  const toggleRecording = () => {
    if (isRecording || mediaRecorderRef.current?.state === 'recording') {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const blobToBase64 = (blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result;
        // Split on comma and take the second part, or return full result if no comma
        const base64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl;
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  const submitRequest = async (audioBase64 = null, inputType = 'text') => {
    const requestPayload = {
      sessionId,
      message: inputType === 'text' ? message : null,
      audioBase64: inputType === 'audio' ? audioBase64 : null,
      inputType,
      context: {
        selectedProductIds: selectedProducts,
        connectorId
      }
    };

    setDebugRequest(JSON.stringify(requestPayload, null, 2));
    setIsLoading(true);

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:4010'}/api/storedesk/assist`,
        requestPayload,
        {
          headers: {
            'Content-Type': 'application/json',
            'X-User-Id': 'test-user-123',
            'X-Tenant-Id': 'test-tenant-456',
            'X-Connector-Id': connectorId,
            'X-User-Email': 'test@example.com',
            'X-User-Permissions': 'read,write'
          }
        }
      );

      setDebugResponse(JSON.stringify(response.data, null, 2));
      
      const newMessage = {
        type: 'user',
        content: inputType === 'text' ? message : '[Audio Message]',
        timestamp: new Date().toISOString()
      };
      
      const aiResponse = {
        type: 'ai',
        content: response.data.message,
        timestamp: new Date().toISOString(),
        provider: response.data.activeProvider,
        actionsExecuted: response.data.actionsExecuted || [],
        requiresConfirmation: response.data.requiresConfirmation || false,
        confirmationQuestion: response.data.confirmationQuestion,
        clarificationQuestion: response.data.clarificationQuestion
      };

      setConversation(prev => [...prev, newMessage, aiResponse]);
      setPendingConfirmation(response.data.requiresConfirmation || false);
      setMessage('');
    } catch (error) {
      console.error('Error:', error);
      setDebugResponse(JSON.stringify({ error: error.message }, null, 2));
      setConversation(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTextSubmit = () => {
    if (!message.trim()) return;
    submitRequest();
  };

  const handleProductToggle = (productId) => {
    setSelectedProducts(prev => 
      prev.includes(productId) 
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    );
  };

  const changeMockScenario = async (scenario) => {
    try {
      await axios.post(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:4010'}/mock/scenario`, 
        { scenario });
      setMockScenario(scenario);
    } catch (error) {
      console.error('Error changing scenario:', error);
    }
  };

  const resetSession = () => {
    setSessionId(generateUUID());
    setConversation([]);
    setSelectedProducts([]);
    setPendingConfirmation(false);
    setDebugRequest(null);
    setDebugResponse(null);
  };

  const clearDebug = () => {
    setDebugRequest(null);
    setDebugResponse(null);
  };

  if (process.env.NEXT_PUBLIC_STOREDESK_TEST_ENABLED !== 'true') {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="sd-panel max-w-md w-full p-8 text-center">
          <p className="font-display text-2xl font-semibold text-ink-900">StoreDesk</p>
          <h1 className="mt-3 text-lg font-medium text-ink-700">Test page disabled</h1>
          <p className="mt-2 text-sm text-ink-500">
            Set <code className="text-teal-700">NEXT_PUBLIC_STOREDESK_TEST_ENABLED=true</code> to enable.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-ink-100/80 bg-white/75 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div>
            <p className="font-display text-2xl font-bold tracking-tight text-ink-950 sm:text-3xl">
              StoreDesk
            </p>
            <p className="mt-0.5 text-sm text-ink-500">AI assist playground</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {pendingConfirmation && (
              <span className="rounded-md bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">
                Awaiting confirmation
              </span>
            )}
            {isRecording && (
              <span className="inline-flex items-center gap-1.5 rounded-md bg-coral-100 px-2.5 py-1 text-xs font-semibold text-coral-600">
                <span className="h-1.5 w-1.5 rounded-sm bg-coral-600" />
                Recording
              </span>
            )}
            <button
              type="button"
              onClick={resetSession}
              disabled={!isClient}
              className="rounded-lg border border-ink-100 bg-white px-3 py-1.5 text-sm font-medium text-ink-700 transition hover:border-ink-300 hover:bg-ink-50 disabled:opacity-50"
            >
              New session
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-5 px-4 py-5 sm:px-6 lg:grid-cols-12 lg:gap-6 lg:py-8">
        {/* Composer */}
        <section className="sd-panel sd-fade-up p-5 sm:p-6 lg:col-span-4">
          <div className="mb-5">
            <h2 className="font-display text-lg font-semibold text-ink-950">Compose</h2>
            <p className="mt-1 text-sm text-ink-500">
              Type a command or use voice. Session stays until you reset.
            </p>
          </div>

          <div className="mb-4 rounded-lg bg-ink-50 px-3 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-500">Session</p>
            <p className="mt-0.5 truncate font-mono text-xs text-ink-700">
              {isClient ? sessionId : 'Loading…'}
            </p>
          </div>

          <label className="mb-4 block">
            <span className="mb-1.5 block text-sm font-medium text-ink-700">Connector ID</span>
            <input
              type="text"
              value={connectorId}
              onChange={(e) => setConnectorId(e.target.value)}
              className="w-full rounded-lg border border-ink-100 bg-white px-3 py-2.5 text-sm text-ink-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
            />
          </label>

          <label className="mb-3 block">
            <span className="mb-1.5 block text-sm font-medium text-ink-700">Message</span>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              disabled={isLoading}
              placeholder={
                pendingConfirmation
                  ? "Say or type 'yes' to confirm, 'no' to cancel…"
                  : 'e.g. Disable stock monitoring for all products'
              }
              className="w-full resize-y rounded-lg border border-ink-100 bg-white px-3 py-2.5 text-sm text-ink-900 outline-none transition placeholder:text-ink-500/70 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 disabled:bg-ink-50"
            />
          </label>

          <div className="mb-6 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleTextSubmit}
              disabled={isLoading || !message.trim()}
              className="inline-flex flex-1 items-center justify-center rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-ink-300 min-w-[8rem]"
            >
              Send
            </button>
            <button
              type="button"
              onClick={toggleRecording}
              disabled={isLoading}
              className={`inline-flex flex-1 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:bg-ink-300 min-w-[8rem] ${
                isRecording
                  ? 'sd-recording bg-coral-600 hover:bg-coral-600'
                  : 'bg-ink-900 hover:bg-ink-950'
              }`}
              title={
                isRecording
                  ? 'Click to stop and send'
                  : pendingConfirmation
                    ? 'Reply by voice: say yes or no'
                    : 'Click to start, speak, then click again to stop'
              }
            >
              {isRecording ? 'Stop voice' : 'Start voice'}
            </button>
          </div>

          <div className="mb-6">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-ink-700">Products</h3>
              <span className="text-xs text-ink-500">{selectedProducts.length} selected</span>
            </div>
            <div className="sd-scroll max-h-40 space-y-1 overflow-y-auto rounded-lg border border-ink-100 bg-white p-2">
              {testProducts.map((product) => {
                const checked = selectedProducts.includes(product.id);
                return (
                  <label
                    key={product.id}
                    className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition ${
                      checked ? 'bg-teal-50 text-teal-700' : 'text-ink-700 hover:bg-ink-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleProductToggle(product.id)}
                      className="h-4 w-4 accent-teal-600"
                    />
                    <span className="font-medium">{product.name}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink-700">Quick prompts</h3>
            <div className="space-y-2">
              {Object.entries(testPrompts).map(([category, prompts]) => (
                <details
                  key={category}
                  className="group rounded-lg border border-ink-100 bg-white open:bg-ink-50/60"
                >
                  <summary className="cursor-pointer list-none px-3 py-2.5 text-sm font-medium text-ink-700 marker:content-none [&::-webkit-details-marker]:hidden">
                    <span className="flex items-center justify-between">
                      {category}
                      <span className="text-ink-500 transition group-open:rotate-180">▾</span>
                    </span>
                  </summary>
                  <div className="space-y-1 border-t border-ink-100 px-2 py-2">
                    {prompts.map((prompt, index) => (
                      <button
                        key={index}
                        type="button"
                        onClick={() => setMessage(prompt)}
                        className="block w-full rounded-md px-2.5 py-2 text-left text-xs leading-snug text-ink-700 transition hover:bg-white hover:text-teal-700"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* Conversation */}
        <section className="sd-panel sd-fade-up flex min-h-[28rem] flex-col p-5 sm:p-6 lg:col-span-5" style={{ animationDelay: '60ms' }}>
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <h2 className="font-display text-lg font-semibold text-ink-950">Conversation</h2>
              <p className="mt-1 text-sm text-ink-500">Live replies from the AI gateway</p>
            </div>
            {conversation.length > 0 && (
              <button
                type="button"
                onClick={() => setConversation([])}
                className="text-xs font-medium text-ink-500 transition hover:text-ink-900"
              >
                Clear
              </button>
            )}
          </div>

          <div className="sd-scroll flex-1 space-y-3 overflow-y-auto pr-1">
            {conversation.length === 0 && !isLoading && (
              <div className="flex h-full min-h-[16rem] flex-col items-center justify-center rounded-xl border border-dashed border-ink-100 bg-ink-50/70 px-6 text-center">
                <p className="font-display text-base font-semibold text-ink-900">No messages yet</p>
                <p className="mt-2 max-w-xs text-sm text-ink-500">
                  Send a text command or record a voice request to see the assist flow here.
                </p>
              </div>
            )}

            {conversation.map((msg, index) => (
              <div
                key={`${msg.timestamp}-${index}`}
                className={`rounded-xl px-3.5 py-3 ${
                  msg.type === 'user'
                    ? 'ml-6 bg-teal-600 text-white'
                    : msg.type === 'error'
                      ? 'bg-coral-100 text-coral-600'
                      : 'mr-6 border border-ink-100 bg-white text-ink-900'
                }`}
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span
                    className={`text-[11px] font-semibold uppercase tracking-wide ${
                      msg.type === 'user' ? 'text-teal-100' : 'text-ink-500'
                    }`}
                  >
                    {msg.type === 'user' ? 'You' : msg.type === 'error' ? 'Error' : 'StoreDesk AI'}
                  </span>
                  {msg.provider && (
                    <span className="rounded bg-ink-50 px-1.5 py-0.5 text-[10px] font-medium text-ink-700">
                      {msg.provider}
                    </span>
                  )}
                </div>
                <p className="text-sm leading-relaxed">{msg.content}</p>

                {msg.actionsExecuted && msg.actionsExecuted.length > 0 && (
                  <ul className="mt-2 space-y-1 border-t border-ink-100 pt-2 text-xs text-ink-700">
                    {msg.actionsExecuted.map((action, i) => (
                      <li key={i}>
                        <span className="font-medium">{action.intent}</span>
                        {' — '}
                        {action.success ? 'Success' : 'Failed'}
                        {action.affectedCount != null && ` (${action.affectedCount} items)`}
                      </li>
                    ))}
                  </ul>
                )}

                {msg.requiresConfirmation && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setMessage('Yes proceed');
                        setTimeout(() => submitRequest(), 100);
                      }}
                      disabled={isLoading}
                      className="rounded-md bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-teal-700 disabled:bg-ink-300"
                    >
                      Confirm
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setMessage('Cancel');
                        setTimeout(() => submitRequest(), 100);
                      }}
                      disabled={isLoading}
                      className="rounded-md border border-ink-100 bg-white px-3 py-1.5 text-xs font-semibold text-ink-700 transition hover:bg-ink-50 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                )}

                {msg.clarificationQuestion && (
                  <div className="mt-2 rounded-md bg-amber-50 px-2.5 py-2 text-xs text-amber-900">
                    <span className="font-semibold">Needs clarification: </span>
                    {msg.clarificationQuestion}
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="mr-6 flex items-center gap-2 rounded-xl border border-ink-100 bg-white px-3.5 py-3 text-sm text-ink-500">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-teal-600 border-t-transparent" />
                Processing…
              </div>
            )}
          </div>
        </section>

        {/* Debug */}
        <section className="sd-panel sd-fade-up p-5 sm:p-6 lg:col-span-3" style={{ animationDelay: '120ms' }}>
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h2 className="font-display text-lg font-semibold text-ink-950">Debug</h2>
              <p className="mt-1 text-sm text-ink-500">Gateway payload & mock scenario</p>
            </div>
            <button
              type="button"
              onClick={clearDebug}
              className="text-xs font-medium text-ink-500 transition hover:text-ink-900"
            >
              Clear
            </button>
          </div>

          <label className="mb-4 block">
            <span className="mb-1.5 block text-sm font-medium text-ink-700">Mock scenario</span>
            <select
              value={mockScenario}
              onChange={(e) => changeMockScenario(e.target.value)}
              className="w-full rounded-lg border border-ink-100 bg-white px-3 py-2.5 text-sm text-ink-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
            >
              <option value="happy_path">Happy path</option>
              <option value="partial_failure">Partial failure</option>
              <option value="full_failure">Full failure</option>
              <option value="slow_response">Slow response</option>
              <option value="server_error">Server error</option>
              <option value="auth_failure">Auth failure</option>
            </select>
          </label>

          <div className="space-y-4">
            <div>
              <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">
                Request
              </h3>
              <pre className="sd-scroll max-h-48 overflow-auto rounded-lg bg-ink-950 p-3 font-mono text-[11px] leading-relaxed text-teal-100">
                {debugRequest || 'No request yet'}
              </pre>
            </div>
            <div>
              <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">
                Response
              </h3>
              <pre className="sd-scroll max-h-48 overflow-auto rounded-lg bg-ink-950 p-3 font-mono text-[11px] leading-relaxed text-teal-100">
                {debugResponse || 'No response yet'}
              </pre>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
