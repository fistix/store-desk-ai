import { useState, useRef } from 'react';
import axios from 'axios';

export default function StoreDeskTest() {
  const [sessionId, setSessionId] = useState(generateUUID());
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
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

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

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioBase64 = await blobToBase64(audioBlob);
        submitRequest(audioBase64, 'audio');
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Could not access microphone');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
    }
  };

  const blobToBase64 = (blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
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
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-md">
          <h1 className="text-2xl font-bold text-gray-800">Test Page Disabled</h1>
          <p className="text-gray-600 mt-2">Set NEXT_PUBLIC_STOREDESK_TEST_ENABLED=true to enable</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">StoreDesk AI Test Interface</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Input Controls */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Input Controls</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Session ID: {sessionId}
              </label>
              <button 
                onClick={resetSession}
                className="bg-blue-500 text-white px-3 py-1 rounded text-sm hover:bg-blue-600"
              >
                Reset Session
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Connector ID
              </label>
              <input
                type="text"
                value={connectorId}
                onChange={(e) => setConnectorId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Message
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                rows={3}
                disabled={isLoading}
                placeholder={pendingConfirmation ? "Type 'yes' to confirm or 'no' to cancel..." : "Type your command here..."}
              />
            </div>

            <div className="mb-4 flex gap-2">
              <button
                onClick={handleTextSubmit}
                disabled={isLoading || !message.trim()}
                className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 disabled:bg-gray-400"
              >
                Submit Text
              </button>
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isLoading || pendingConfirmation}
                className={`px-4 py-2 rounded text-white ${
                  isRecording ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-500 hover:bg-blue-600'
                } disabled:bg-gray-400`}
              >
                {isRecording ? 'Stop Recording' : 'Start Voice'}
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Selected Products
              </label>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {testProducts.map(product => (
                  <label key={product.id} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={selectedProducts.includes(product.id)}
                      onChange={() => handleProductToggle(product.id)}
                      className="mr-2"
                    />
                    <span className="text-sm">{product.name}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Test Prompts
              </label>
              <div className="space-y-2">
                {Object.entries(testPrompts).map(([category, prompts]) => (
                  <details key={category} className="border border-gray-200 rounded p-2">
                    <summary className="cursor-pointer text-sm font-medium">{category}</summary>
                    <div className="mt-2 space-y-1">
                      {prompts.map((prompt, index) => (
                        <button
                          key={index}
                          onClick={() => setMessage(prompt)}
                          className="block w-full text-left text-xs bg-gray-50 hover:bg-gray-100 p-1 rounded"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </details>
                ))}
              </div>
            </div>
          </div>

          {/* Middle Panel - Conversation */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Conversation</h2>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {conversation.map((msg, index) => (
                <div key={index} className={`p-3 rounded-lg ${
                  msg.type === 'user' ? 'bg-blue-100 ml-8' :
                  msg.type === 'error' ? 'bg-red-100' : 'bg-gray-100 mr-8'
                }`}>
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-medium text-sm">
                      {msg.type === 'user' ? 'User' : 
                       msg.type === 'error' ? 'Error' : 'StoreDesk AI'}
                    </span>
                    {msg.provider && (
                      <span className="text-xs bg-purple-200 px-2 py-1 rounded">
                        {msg.provider}
                      </span>
                    )}
                  </div>
                  <p className="text-sm">{msg.content}</p>
                  {msg.actionsExecuted && msg.actionsExecuted.length > 0 && (
                    <div className="mt-2 text-xs">
                      <strong>Actions:</strong>
                      <ul className="ml-2">
                        {msg.actionsExecuted.map((action, i) => (
                          <li key={i}>
                            {action.intent} - {action.success ? 'Success' : 'Failed'} 
                            {action.affectedCount && ` (${action.affectedCount} items)`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {msg.requiresConfirmation && (
                    <div className="mt-3 space-x-2">
                      <button 
                        onClick={() => {
                          setMessage('Yes proceed');
                          setTimeout(() => submitRequest(), 100);
                        }}
                        disabled={isLoading}
                        className="bg-green-500 text-white px-3 py-1 rounded text-xs hover:bg-green-600 disabled:bg-gray-400"
                      >
                        Confirm
                      </button>
                      <button 
                        onClick={() => {
                          setMessage('Cancel');
                          setTimeout(() => submitRequest(), 100);
                        }}
                        disabled={isLoading}
                        className="bg-red-500 text-white px-3 py-1 rounded text-xs hover:bg-red-600 disabled:bg-gray-400"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                  {msg.clarificationQuestion && (
                    <div className="mt-2 p-2 bg-yellow-100 rounded text-xs">
                      <strong>Clarification needed:</strong> {msg.clarificationQuestion}
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="bg-gray-100 p-3 rounded-lg mr-8">
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mr-2"></div>
                    <span className="text-sm">Processing...</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Debug */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Debug</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Mock Scenario: {mockScenario}
              </label>
              <select 
                value={mockScenario}
                onChange={(e) => changeMockScenario(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="happy_path">Happy Path</option>
                <option value="partial_failure">Partial Failure</option>
                <option value="full_failure">Full Failure</option>
                <option value="slow_response">Slow Response</option>
                <option value="server_error">Server Error</option>
                <option value="auth_failure">Auth Failure</option>
              </select>
            </div>

            <div className="mb-4 space-y-2">
              <button 
                onClick={clearDebug}
                className="bg-gray-500 text-white px-3 py-1 rounded text-sm hover:bg-gray-600"
              >
                Clear Debug
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium mb-2">Request Payload:</h3>
                <pre className="bg-gray-50 p-2 rounded text-xs overflow-x-auto max-h-40">
                  {debugRequest || 'No request yet'}
                </pre>
              </div>
              
              <div>
                <h3 className="text-sm font-medium mb-2">Response:</h3>
                <pre className="bg-gray-50 p-2 rounded text-xs overflow-x-auto max-h-40">
                  {debugResponse || 'No response yet'}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
