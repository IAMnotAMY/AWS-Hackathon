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
}

// AI Agent API configuration from .env
const AI_AGENT_CONFIG = {
  apiUrl: import.meta.env.VITE_API_URL,
  region: import.meta.env.VITE_AWS_REGION,
  accessKeyId: import.meta.env.VITE_AWS_ACCESS_KEY_ID,
  secretAccessKey: import.meta.env.VITE_AWS_SECRET_ACCESS_KEY,
  lambdaFunctions: {
    getProject: import.meta.env.VITE_LAMBDA_GET_PROJECT,
    createProject: import.meta.env.VITE_LAMBDA_CREATE_PROJECT,
    updateProject: import.meta.env.VITE_LAMBDA_UPDATE_PROJECT,
    generatePresignedUrl: import.meta.env.VITE_LAMBDA_GENERATE_PRESIGNED_URL
  }
};

const Chatbot = ({ projectId }: ChatbotProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: `Hello! I'm your AI assistant for project ${projectId}. I can help you with questions about your 3D model, building design, or any modifications you'd like to make. How can I assist you today?`,
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
        text: aiResponse.message || 'I received your request and processed it.',
        sender: 'bot',
        timestamp: new Date(),
        json: aiResponse.json // Store JSON response if available
      };
      
      setMessages(prev => [...prev, botMessage]);
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

  // AI Agent API call function
  const callAIAgent = async (userPrompt: string, projectId: string) => {
    const apiUrl = AI_AGENT_CONFIG.apiUrl;
    
    // Determine which Lambda function to call based on user intent
    const intent = analyzeUserIntent(userPrompt);
    
    const requestBody = {
      prompt: userPrompt,
      projectId: projectId,
      intent: intent,
      timestamp: new Date().toISOString()
    };

    const response = await fetch(`${apiUrl}/ai-agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${AI_AGENT_CONFIG.accessKeyId}`, // Simplified auth
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`AI Agent API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    
    // Expected response format:
    // {
    //   message: "Human readable response",
    //   json: { ... }, // JSON data (building modifications, etc.)
    //   success: true
    // }
    
    return data;
  };

  // Analyze user intent to determine appropriate Lambda function
  const analyzeUserIntent = (prompt: string): string => {
    const lowerPrompt = prompt.toLowerCase();
    
    if (lowerPrompt.includes('generate') || lowerPrompt.includes('create') || lowerPrompt.includes('new')) {
      return 'generate';
    }
    if (lowerPrompt.includes('modify') || lowerPrompt.includes('change') || lowerPrompt.includes('update')) {
      return 'modify';
    }
    if (lowerPrompt.includes('get') || lowerPrompt.includes('show') || lowerPrompt.includes('display')) {
      return 'retrieve';
    }
    if (lowerPrompt.includes('url') || lowerPrompt.includes('download') || lowerPrompt.includes('export')) {
      return 'export';
    }
    
    return 'general'; // Default intent
  };

  const generateBotResponse = (userInput: string): string => {
    const input = userInput.toLowerCase();
    
    if (input.includes('window') || input.includes('door')) {
      return "I can see your building has windows and doors in the 3D model. Would you like me to help you modify their positions, add new ones, or change their properties like size or style?";
    }
    
    if (input.includes('room') || input.includes('space')) {
      return "Your floorspace design includes different room types. I can help you understand the room layout, suggest improvements, or help you modify room dimensions and purposes.";
    }
    
    if (input.includes('3d') || input.includes('model') || input.includes('view')) {
      return "The 3D viewer shows your complete building model with walls, windows, doors, and shading elements. You can rotate, zoom, and pan to explore different angles. Would you like tips on navigating the 3D view?";
    }
    
    if (input.includes('change') || input.includes('modify') || input.includes('edit')) {
      return "I can help you understand how to modify your building design. What specific changes would you like to make? For example, moving windows, changing room sizes, or adding new elements?";
    }
    
    if (input.includes('help') || input.includes('how')) {
      return "I'm here to help! I can assist with:\n• Understanding your 3D building model\n• Explaining room layouts and dimensions\n• Suggesting design improvements\n• Helping with window and door placement\n• Answering questions about building elements\n\nWhat would you like to know more about?";
    }
    
    if (input.includes('hello') || input.includes('hi')) {
      return "Hello! I'm excited to help you with your building design. Your 3D model looks great! Is there anything specific you'd like to explore or modify?";
    }
    
    // Default responses
    const responses = [
      "That's an interesting question about your building design. Could you provide more details about what you'd like to know?",
      "I'd be happy to help you with that! Can you tell me more about what you're trying to achieve with your 3D model?",
      "Great question! Your building design has many possibilities. What specific aspect would you like to focus on?",
      "I can help you understand and improve your floorspace design. What particular element interests you most?",
      "Let me help you with that. Are you looking to modify the existing design or understand how something works?"
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
                      📄 Generated JSON:
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
                        // Could add a toast notification here
                      }}
                      style={{
                        marginTop: '8px',
                        padding: '4px 8px',
                        fontSize: '10px',
                        background: '#007bff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      Copy JSON
                    </button>
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
              onKeyPress={handleKeyPress}
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