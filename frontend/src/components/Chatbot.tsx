/**
 * Chatbot Component with AI Agent Integration
 * 
 * This chatbot connects to AWS Lambda functions to process user prompts
 * and return JSON responses for building modifications.
 * 
 * CONFIGURATION:
 * - API endpoint: VITE_API_URL from .env
 * - AWS Region: VITE_AWS_REGION from .env
 * - Lambda functions configured in .env:
 *   - VITE_LAMBDA_GET_PROJECT
 *   - VITE_LAMBDA_CREATE_PROJECT
 *   - VITE_LAMBDA_UPDATE_PROJECT
 *   - VITE_LAMBDA_GENERATE_PRESIGNED_URL
 * 
 * FLOW:
 * 1. User types prompt in textarea
 * 2. handleSendMessage() captures the prompt
 * 3. callAIAgent() sends prompt to Lambda via API Gateway
 * 4. AI Agent processes prompt and returns:
 *    {
 *      message: "Human readable response",
 *      json: { ... building data ... },
 *      success: true
 *    }
 * 5. Response displayed with JSON viewer
 * 
 * API ENDPOINT EXPECTED:
 * POST ${VITE_API_URL}/ai-agent
 * Body: {
 *   prompt: string,
 *   projectId: string,
 *   intent: string,
 *   timestamp: string
 * }
 * 
 * BACKEND SETUP NEEDED:
 * - Create Lambda function that accepts user prompts
 * - Process prompts with AI (e.g., Bedrock, OpenAI)
 * - Return JSON building modifications
 * - Configure API Gateway route: POST /ai-agent
 */

import { useState, useRef, useEffect } from 'react';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  json?: any; // Add support for JSON responses
}

interface ChatbotProps {
  projectId: string;
  onJsonReceived?: (jsonData: any) => void; // Callback to send JSON to 3D viewer
}

const Chatbot = ({ projectId, onJsonReceived }: ChatbotProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: `🏠 Hello! I'm your AI Room Generator for project ${projectId}. 

I can instantly create rooms and display them in the 3D viewer! Just tell me what you want:
• "Create a room of 4 by 5 m"
• "Make a bedroom 3x4 meters with 2 windows"
• "Generate a living room 6x8m with a door"

I'll generate the room and show it directly in the 3D viewer! 🎉`,
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputText;
    setInputText('');
    setIsTyping(true);

    try {
      // Call AI Agent Lambda function
      const aiResponse = await callAIAgent(currentInput, projectId);
      
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: aiResponse.message || '✅ Room generated successfully!',
        sender: 'bot',
        timestamp: new Date(),
        json: aiResponse.json // Store JSON response if available
      };
      
      setMessages(prev => [...prev, botMessage]);
      
      // If we have JSON data, send it to the 3D viewer immediately
      if (aiResponse.json && onJsonReceived) {
        console.log('Loading room data into 3D viewer:', aiResponse.json);
        onJsonReceived(aiResponse.json);
      }
      
      // Only auto-download if explicitly requested (disabled by default now)
      if (aiResponse.autoDownload && aiResponse.json) {
        downloadRoomFile(aiResponse.json, currentInput);
      }
    } catch (error) {
      console.error('AI Agent error:', error);
      
      // Fallback to local response if API fails
      const fallbackResponse = generateBotResponse(currentInput);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `I'm having trouble connecting to the AI service right now. Here's what I can tell you locally:\n\n${fallbackResponse}`,
        sender: 'bot',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, botMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  // AI Agent API call function - connects to localhost:8000/generate-room
  const callAIAgent = async (userPrompt: string, projectId: string) => {
    // Try the original /process endpoint first, then /generate-room if that fails
    let requestBody = {
      message: userPrompt,
      session_id: projectId
    };

    console.log('Trying /process endpoint with:', requestBody);

    let response = await fetch('http://localhost:8000/process', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    // If /process fails, try /generate-room with different format
    if (!response.ok) {
      console.log('/process failed, trying /generate-room');
      requestBody = {
        message: userPrompt,
        session_id: projectId
      };

      console.log('Trying /generate-room endpoint with:', requestBody);

      response = await fetch('http://localhost:8000/generate-room', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });
    }

    if (!response.ok) {
      // Try to get the error details
      let errorMessage = `AI Agent API error: ${response.status} ${response.statusText}`;
      try {
        const errorData = await response.text();
        if (errorData) {
          errorMessage += ` - ${errorData}`;
        }
      } catch (e) {
        // Ignore parsing errors
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    console.log('AI Agent response:', data);
    
    // Handle both response formats
    if (data.question || data.needs_clarification) {
      // Original format with clarification
      return {
        message: data.question || "I've processed your request.",
        json: data.memory_summary || data,
        success: true,
        session_id: data.session_id,
        needs_clarification: data.needs_clarification
      };
    } else {
      // Direct room generation format
      return {
        message: `✅ Room generated successfully! ${userPrompt}`,
        json: data,
        success: true,
        autoDownload: false // Disable auto-download, just show in viewer
      };
    }
  };

  // Auto-download room file function
  const downloadRoomFile = (roomData: any, prompt: string) => {
    try {
      const dataStr = JSON.stringify(roomData, null, 2);
      const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
      
      // Generate filename based on prompt
      const sanitizedPrompt = prompt.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30);
      const timestamp = new Date().toISOString().slice(0, 10);
      const filename = `room_${sanitizedPrompt}_${timestamp}.json`;
      
      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', dataUri);
      linkElement.setAttribute('download', filename);
      linkElement.style.display = 'none';
      document.body.appendChild(linkElement);
      linkElement.click();
      document.body.removeChild(linkElement);
      
      console.log(`✅ Room file downloaded: ${filename}`);
    } catch (error) {
      console.error('Error downloading room file:', error);
    }
  };

  const generateBotResponse = (userInput: string): string => {
    const input = userInput.toLowerCase();
    
    if (input.includes('room') || input.includes('create') || input.includes('generate')) {
      return "🏠 I can generate rooms instantly and show them in the 3D viewer! Try saying:\n• 'Create a room of 4 by 5 m'\n• 'Make a bedroom 3x4 meters'\n• 'Generate a living room 6x8m with windows'\n\nI'll create the room and display it directly in the viewer!";
    }
    
    if (input.includes('window') || input.includes('door')) {
      return "🚪 I can add windows and doors to your rooms! Just specify:\n• Room dimensions\n• Number and type of windows/doors\n• Their positions\n\nExample: 'Create a 5x4m room with 2 windows and 1 door'";
    }
    
    if (input.includes('size') || input.includes('dimension') || input.includes('meter') || input.includes('m')) {
      return "📏 Perfect! I work with metric dimensions. Tell me the room size like:\n• '4 by 5 meters'\n• '3x4m'\n• '6 by 8 m'\n\nI'll generate the complete room instantly!";
    }
    
    if (input.includes('download') || input.includes('file') || input.includes('json')) {
      return "💾 I automatically provide instant downloads of generated rooms as JSON files! Each room comes with:\n• Complete Floorspace JSON format\n• Ready for 3D visualization\n• Automatic filename with timestamp";
    }
    
    if (input.includes('help') || input.includes('how')) {
      return "🎉 I'm your AI Room Generator! I can:\n• Generate rooms instantly (90% auto-resolved)\n• Display rooms directly in 3D viewer\n• Create complete Floorspace JSON\n• Provide download option if needed\n\nJust tell me: 'Create a room of [width] by [height] m'";
    }
    
    // Default responses focused on room generation
    const responses = [
      "🏠 Ready to generate a room! Just tell me the dimensions like '4 by 5 meters' and I'll show it in the 3D viewer!",
      "✨ I can create any room size you need! Try: 'Create a room of 3 by 4 m' and watch it appear in the viewer!",
      "🎯 Let's build something! Specify room dimensions and I'll generate it directly in the 3D viewer!",
      "🚀 I'm optimized for instant room generation! Tell me the size and I'll display it in the viewer immediately!"
    ];
    
    return responses[Math.floor(Math.random() * responses.length)];
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
  };

  return (
    <>
      {/* Chat Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #007bff 0%, #0056b3 100%)',
          border: 'none',
          color: 'white',
          cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(0, 123, 255, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px',
          transition: 'all 0.3s ease',
          zIndex: 1000
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.transform = 'scale(1.1)';
          e.currentTarget.style.boxShadow = '0 6px 16px rgba(0, 123, 255, 0.4)';
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 123, 255, 0.3)';
        }}
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '100px',
            right: '24px',
            width: '380px',
            height: '500px',
            background: 'white',
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.15)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 999,
            overflow: 'hidden'
          }}
        >
          {/* Chat Header */}
          <div
            style={{
              background: 'linear-gradient(135deg, #007bff 0%, #0056b3 100%)',
              color: 'white',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: '600', margin: 0 }}>
                AI Building Assistant
              </h3>
              <p style={{ fontSize: '12px', opacity: 0.9, margin: 0 }}>
                Project: {projectId}
              </p>
            </div>
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#4CAF50',
                boxShadow: '0 0 0 2px rgba(76, 175, 80, 0.3)'
              }}
            />
          </div>

          {/* Messages Area */}
          <div
            style={{
              flex: 1,
              padding: '16px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}
          >
            {messages.map((message) => (
              <div
                key={message.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: message.sender === 'user' ? 'flex-end' : 'flex-start'
                }}
              >
                <div
                  style={{
                    maxWidth: '80%',
                    padding: '12px 16px',
                    borderRadius: message.sender === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    background: message.sender === 'user' 
                      ? 'linear-gradient(135deg, #007bff 0%, #0056b3 100%)' 
                      : '#f1f3f5',
                    color: message.sender === 'user' ? 'white' : '#333',
                    fontSize: '14px',
                    lineHeight: '1.4',
                    whiteSpace: 'pre-wrap'
                  }}
                >
                  {message.text}
                </div>
                
                {/* Display JSON response if available */}
                {message.json && (
                  <div
                    style={{
                      maxWidth: '80%',
                      marginTop: '8px',
                      padding: '12px',
                      background: '#f8f9fa',
                      border: '1px solid #e9ecef',
                      borderRadius: '8px',
                      fontSize: '12px',
                      fontFamily: 'monospace'
                    }}
                  >
                    <div style={{ 
                      fontSize: '11px', 
                      fontWeight: '600', 
                      color: '#666', 
                      marginBottom: '8px',
                      fontFamily: 'inherit'
                    }}>
                      🏠 Generated Room Data:
                    </div>
                    <pre style={{ 
                      margin: 0, 
                      whiteSpace: 'pre-wrap', 
                      wordBreak: 'break-word',
                      maxHeight: '200px',
                      overflowY: 'auto'
                    }}>
                      {JSON.stringify(message.json, null, 2)}
                    </pre>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(JSON.stringify(message.json, null, 2));
                      }}
                      style={{
                        marginTop: '8px',
                        marginRight: '8px',
                        padding: '4px 8px',
                        fontSize: '10px',
                        background: '#007bff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      📋 Copy
                    </button>
                    <button
                      onClick={() => downloadRoomFile(message.json, 'room')}
                      style={{
                        marginTop: '8px',
                        marginRight: '8px',
                        padding: '4px 8px',
                        fontSize: '10px',
                        background: '#17a2b8',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      💾 Download
                    </button>
                    {onJsonReceived && (
                      <button
                        onClick={() => onJsonReceived(message.json)}
                        style={{
                          marginTop: '8px',
                          padding: '4px 8px',
                          fontSize: '10px',
                          background: '#28a745',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        🏗️ Load in 3D
                      </button>
                    )}
                  </div>
                )}
                
                <span
                  style={{
                    fontSize: '11px',
                    color: '#999',
                    marginTop: '4px',
                    marginLeft: message.sender === 'user' ? '0' : '8px',
                    marginRight: message.sender === 'user' ? '8px' : '0'
                  }}
                >
                  {formatTime(message.timestamp)}
                </span>
              </div>
            ))}

            {/* Typing Indicator */}
            {isTyping && (
              <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                <div
                  style={{
                    padding: '12px 16px',
                    borderRadius: '18px 18px 18px 4px',
                    background: '#f1f3f5',
                    display: 'flex',
                    gap: '4px',
                    alignItems: 'center'
                  }}
                >
                  <div
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: '#999',
                      animation: 'pulse 1.4s ease-in-out infinite'
                    }}
                  />
                  <div
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: '#999',
                      animation: 'pulse 1.4s ease-in-out 0.2s infinite'
                    }}
                  />
                  <div
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: '#999',
                      animation: 'pulse 1.4s ease-in-out 0.4s infinite'
                    }}
                  />
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div
            style={{
              padding: '16px',
              borderTop: '1px solid #eee',
              display: 'flex',
              gap: '8px',
              alignItems: 'flex-end'
            }}
          >
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Ask me about your building design..."
              style={{
                flex: 1,
                minHeight: '20px',
                maxHeight: '80px',
                padding: '12px',
                border: '1px solid #ddd',
                borderRadius: '20px',
                fontSize: '14px',
                resize: 'none',
                outline: 'none',
                fontFamily: 'inherit'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#007bff';
                e.target.style.boxShadow = '0 0 0 3px rgba(0, 123, 255, 0.1)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#ddd';
                e.target.style.boxShadow = 'none';
              }}
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputText.trim() || isTyping}
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                border: 'none',
                background: inputText.trim() && !isTyping 
                  ? 'linear-gradient(135deg, #007bff 0%, #0056b3 100%)' 
                  : '#ccc',
                color: 'white',
                cursor: inputText.trim() && !isTyping ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '16px',
                transition: 'all 0.2s ease'
              }}
            >
              ➤
            </button>
          </div>
        </div>
      )}

      {/* CSS Animation for typing indicator */}
      <style>{`
        @keyframes pulse {
          0%, 60%, 100% {
            transform: scale(1);
            opacity: 0.4;
          }
          30% {
            transform: scale(1.2);
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
};

export default Chatbot;