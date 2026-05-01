import { useState, useRef } from 'react';
import axios from 'axios';

export default function VoiceTest() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [audioBase64, setAudioBase64] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

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
        const base64 = await blobToBase64(audioBlob);
        setAudioBase64(base64);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setError('');
    } catch (error) {
      console.error('Error starting recording:', error);
      setError('Could not access microphone');
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

  const transcribeAudio = async () => {
    if (!audioBase64.trim()) {
      setError('Please record audio first');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:4010'}/api/storedesk/voice-to-text`,
        { audioBase64 },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      setTranscription(response.data.text);
      if (!response.data.success) {
        setError(response.data.error);
      }
    } catch (error) {
      console.error('Error:', error);
      setError(error.message || 'Transcription failed');
    } finally {
      setIsLoading(false);
    }
  };

  const clearAll = () => {
    setTranscription('');
    setAudioBase64('');
    setError('');
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Voice-to-Text Test</h1>
        
        <div className="bg-white rounded-lg shadow-md p-6">
          {/* Recording Controls */}
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">Recording Controls</h2>
            
            <div className="flex gap-4 mb-4">
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isLoading}
                className={`px-6 py-3 rounded-lg text-white font-medium ${
                  isRecording 
                    ? 'bg-red-500 hover:bg-red-600' 
                    : 'bg-blue-500 hover:bg-blue-600'
                } disabled:bg-gray-400`}
              >
                {isRecording ? 'Stop Recording' : 'Start Recording'}
              </button>
              
              <button
                onClick={transcribeAudio}
                disabled={isLoading || !audioBase64.trim()}
                className="bg-green-500 text-white px-6 py-3 rounded-lg hover:bg-green-600 disabled:bg-gray-400 font-medium"
              >
                {isLoading ? 'Transcribing...' : 'Transcribe'}
              </button>
              
              <button
                onClick={clearAll}
                className="bg-gray-500 text-white px-6 py-3 rounded-lg hover:bg-gray-600 font-medium"
              >
                Clear
              </button>
            </div>

            {isRecording && (
              <div className="flex items-center">
                <div className="animate-pulse flex h-3 w-3 bg-red-500 rounded-full mr-2"></div>
                <span className="text-red-500 font-medium">Recording...</span>
              </div>
            )}
          </div>

          {/* Audio Info */}
          <div className="mb-6">
            <h3 className="text-lg font-medium mb-2">Audio Info</h3>
            <div className="bg-gray-50 p-3 rounded">
              <p className="text-sm text-gray-600">
                Audio Base64 Length: {audioBase64.length} characters
              </p>
              {audioBase64.length > 0 && (
                <p className="text-sm text-green-600 mt-1">
                  ✅ Audio captured successfully
                </p>
              )}
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-6">
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                <strong>Error:</strong> {error}
              </div>
            </div>
          )}

          {/* Transcription Result */}
          <div className="mb-6">
            <h3 className="text-lg font-medium mb-2">Transcription Result</h3>
            <div className="bg-gray-50 p-4 rounded min-h-24">
              {transcription ? (
                <div>
                  <p className="text-gray-800 whitespace-pre-wrap">{transcription}</p>
                  <div className="mt-2 text-sm text-gray-600">
                    Characters: {transcription.length}
                  </div>
                </div>
              ) : (
                <p className="text-gray-500 italic">No transcription yet. Record audio and click "Transcribe".</p>
              )}
            </div>
          </div>

          {/* Instructions */}
          <div className="bg-blue-50 p-4 rounded">
            <h3 className="text-lg font-medium mb-2 text-blue-800">Instructions</h3>
            <ol className="list-decimal list-inside text-sm text-blue-700 space-y-1">
              <li>Click "Start Recording" to begin capturing audio</li>
              <li>Speak clearly into your microphone</li>
              <li>Click "Stop Recording" when finished</li>
              <li>Click "Transcribe" to convert audio to text</li>
              <li>Results will appear in the Transcription Result section</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
